import asyncio
from datetime import datetime, timedelta, date, time
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import Schedule, Poll, PollMessage, Attendance, GroupMembership, User, Group
from bot.logger import logger
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.bot_instance import get_bot

# Лимит на одновременную отправку сообщений
MAX_CONCURRENT_SENDS = 20

async def check_upcoming_lessons():
    bot = get_bot()
    now = datetime.now()
    today = now.date()

    async with async_session() as session:
        start_window = (now + timedelta(minutes=4)).time()
        end_window = (now + timedelta(minutes=6)).time()

        stmt = select(Schedule).where(
            Schedule.date == today,
            Schedule.time_start >= start_window,
            Schedule.time_start < end_window
        )
        schedules = (await session.execute(stmt)).scalars().all()

        for sched in schedules:
            existing_poll = await session.scalar(
                select(Poll).where(Poll.schedule_id == sched.id)
            )
            if existing_poll:
                continue

            # Создаём опрос
            active_until = datetime.combine(today, time(23, 59, 59)) + timedelta(days=2)
            poll = Poll(
                schedule_id=sched.id,
                active_until=active_until,
                status='active'
            )
            session.add(poll)
            await session.flush()  # получаем poll.id

            group = await session.get(Group, sched.group_id)
            if not group:
                logger.error(f"Group not found for schedule {sched.id}")
                continue

            members = (await session.execute(
                select(GroupMembership).where(
                    GroupMembership.group_id == group.id,
                    GroupMembership.user_id.isnot(None)
                )
            )).scalars().all()

            if not members:
                logger.info(f"No students in group {group.name} for poll")
                continue

            text = (
                f"📚 *{sched.discipline}* ({sched.type})\n"
                f"🕒 {sched.time_start.strftime('%H:%M')} – {sched.time_end.strftime('%H:%M')}\n"
                f"🏫 {sched.audience or 'не указана'}\n"
                f"👨‍🏫 {sched.teacher or 'не указан'}\n"
                f"\nПожалуйста, отметьте присутствие:"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Присутствую", callback_data=f"poll_{poll.id}_present")],
                [InlineKeyboardButton(text="❌ Отсутствую", callback_data=f"poll_{poll.id}_absent")]
            ])

            # Отправляем сообщения и собираем результаты
            sem = asyncio.Semaphore(MAX_CONCURRENT_SENDS)
            async def send_to_user(member):
                async with sem:
                    try:
                        msg = await bot.send_message(
                            chat_id=member.user_id,
                            text=text,
                            reply_markup=keyboard,
                            parse_mode='Markdown'
                        )
                        return (member.user_id, msg.message_id)
                    except Exception as e:
                        logger.error(f"Failed to send poll to {member.user_id}: {e}")
                        return None

            tasks = [send_to_user(m) for m in members]
            results = await asyncio.gather(*tasks)

            # Сохраняем сообщения в той же сессии
            for result in results:
                if result is not None:
                    user_id, msg_id = result
                    session.add(PollMessage(
                        poll_id=poll.id,
                        user_id=user_id,
                        message_id=msg_id
                    ))

            await session.commit()
            logger.info(f"Poll created for schedule {sched.id} ({sched.discipline})")


async def close_expired_polls():
    """Закрывает опросы с истекшим сроком и проставляет 'absent' неответившим."""
    async with async_session() as session:
        now = datetime.now()
        stmt = select(Poll).where(Poll.status == 'active', Poll.active_until <= now)
        expired_polls = (await session.execute(stmt)).scalars().all()

        for poll in expired_polls:
            poll.status = 'finished'
            # Найти всех студентов, которым отправлялось сообщение, но ответа нет
            poll_messages = (await session.execute(
                select(PollMessage).where(PollMessage.poll_id == poll.id)
            )).scalars().all()

            for pm in poll_messages:
                existing_attendance = await session.get(Attendance, (poll.id, pm.user_id))
                if not existing_attendance:
                    # Проставляем absent
                    session.add(Attendance(
                        poll_id=poll.id,
                        user_id=pm.user_id,
                        status='absent'
                    ))
        await session.commit()
        logger.info(f"Closed {len(expired_polls)} expired polls")