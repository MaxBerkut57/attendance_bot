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
    """Проверяет расписание и создаёт опросы за 5 минут до начала."""
    bot = get_bot()
    now = datetime.now()
    target_time = (now + timedelta(minutes=5)).time()
    today = now.date()

    async with async_session() as session:
        # Ищем занятия на сегодня, которые начнутся ровно через 5 минут
        stmt = select(Schedule).where(
            Schedule.date == today,
            Schedule.time_start == target_time
        )
        schedules = (await session.execute(stmt)).scalars().all()

        for sched in schedules:
            # Проверяем, есть ли уже активный или завершённый опрос для этого занятия
            existing_poll = await session.scalar(
                select(Poll).where(Poll.schedule_id == sched.id)
            )
            if existing_poll:
                continue  # опрос уже создан

            # Создаём опрос
            active_until = datetime.combine(today, time(23, 59, 59)) + timedelta(days=2)  # +2 дня
            poll = Poll(
                schedule_id=sched.id,
                active_until=active_until,
                status='active'
            )
            session.add(poll)
            await session.flush()  # чтобы получить poll.id

            # Получаем группу и студентов
            group = await session.get(Group, sched.group_id)
            if not group:
                logger.error(f"Group not found for schedule {sched.id}")
                continue

            # Все студенты группы (включая старосту, который уже в memberships)
            members = (await session.execute(
                select(GroupMembership).where(
                    GroupMembership.group_id == group.id,
                    GroupMembership.user_id.isnot(None)  # только привязанные
                )
            )).scalars().all()

            if not members:
                logger.info(f"No students in group {group.name} for poll")
                continue

            # Формируем текст опроса
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

            # Рассылаем сообщения студентам с контролем скорости
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
                        # Сохраняем message_id в poll_messages
                        poll_msg = PollMessage(
                            poll_id=poll.id,
                            user_id=member.user_id,
                            message_id=msg.message_id
                        )
                        async with async_session() as session_inner:
                            session_inner.add(poll_msg)
                            await session_inner.commit()
                    except Exception as e:
                        logger.error(f"Failed to send poll to {member.user_id}: {e}")

            tasks = [send_to_user(m) for m in members]
            await asyncio.gather(*tasks)

            # Сохраняем основную транзакцию
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