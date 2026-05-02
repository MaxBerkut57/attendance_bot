from aiogram import Router, types, F
from sqlalchemy import select
from bot.db.database import async_session
from bot.logger import logger
from bot.db.models import Poll, PollMessage, Attendance, User, Group, GroupMembership, Schedule

router = Router()

@router.callback_query(F.data.startswith("poll_"))
async def handle_poll_answer(callback: types.CallbackQuery):
    # Разбираем callback_data: poll_<id>_<status>
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Некорректные данные.")
        return
    poll_id = int(parts[1])
    status = parts[2]  # 'present' или 'absent'

    user_id = callback.from_user.id

    async with async_session() as session:
        # Проверяем, что опрос существует и активен
        poll = await session.get(Poll, poll_id)
        if not poll:
            await callback.answer("Опрос не найден.")
            return
        if poll.status != 'active':
            # Опрос уже закрыт – сообщаем контакты старосты
            group = (await session.execute(
                select(Group).join(Schedule).where(Schedule.id == poll.schedule_id)
            )).scalars().first()
            starosta = await session.get(User, group.starosta_id) if group else None
            await callback.answer(
                f"Опрос закрыт. Свяжитесь со старостой: @{starosta.username or 'нет'}" if starosta else "Опрос закрыт."
            )
            return

        # Проверяем, что пользователь состоит в группе этого занятия
        membership = (await session.execute(
            select(GroupMembership).where(
                GroupMembership.user_id == user_id,
                GroupMembership.group_id == poll.schedule.group_id
            )
        )).scalars().first()
        if not membership:
            await callback.answer("Вы не относитесь к этой группе.")
            return

        # Сохраняем или обновляем ответ
        attendance = await session.get(Attendance, (poll_id, user_id))
        if not attendance:
            attendance = Attendance(poll_id=poll_id, user_id=user_id, status=status)
            session.add(attendance)
        else:
            attendance.status = status
        await session.commit()

    # Подтверждаем пользователю
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ Вы отметились как *{'присутствующий' if status == 'present' else 'отсутствующий'}*.",
        parse_mode='Markdown'
    )
    await callback.answer(f"Отмечено: {'присутствую' if status == 'present' else 'отсутствую'}")