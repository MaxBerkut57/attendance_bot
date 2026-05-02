from aiogram import Router, types, F
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import Poll, PollMessage, Attendance, User, Group, GroupMembership, Schedule
from bot.logger import logger

router = Router()

@router.callback_query(F.data.startswith("poll_"))
async def handle_poll_answer(callback: types.CallbackQuery):
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
            # Опрос закрыт — узнаём группу через явный запрос
            schedule = await session.get(Schedule, poll.schedule_id)
            if schedule:
                group = await session.get(Group, schedule.group_id)
                starosta = await session.get(User, group.starosta_id) if group and group.starosta_id else None
                await callback.answer(
                    f"Опрос закрыт. Свяжитесь со старостой: @{starosta.username or 'нет'}" if starosta else "Опрос закрыт."
                )
            else:
                await callback.answer("Опрос закрыт.")
            return

        # Получаем group_id через schedule_id
        schedule = await session.get(Schedule, poll.schedule_id)
        if not schedule:
            await callback.answer("Ошибка: расписание не найдено.")
            return
        group_id = schedule.group_id

        user = (await session.execute(select(User).where(User.user_id == user_id))).scalars().first()
        if not user:
            await callback.answer("Пользователь не найден.")
            return

        membership = (await session.execute(
            select(GroupMembership).where(
                GroupMembership.user_id == user_id,
                GroupMembership.group_id == group_id
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
    current_status_emoji = "✅" if status == 'present' else "❌"
    new_text = (
            callback.message.text.split("\n\n")[0] +  # исходный текст опроса
            f"\n\n{current_status_emoji} Вы отметились как *{'присутствующий' if status == 'present' else 'отсутствующий'}*.\n"
            "_Вы можете изменить ответ до закрытия опроса._"
    )
    # Оставляем ту же клавиатуру, что и в исходном сообщении
    await callback.message.edit_text(
        new_text,
        parse_mode='Markdown',
        reply_markup=callback.message.reply_markup  # та же клавиатура
    )
    await callback.answer(f"Отмечено: {'присутствую' if status == 'present' else 'отсутствую'}")