from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete
from bot.db.database import async_session
from bot.db.models import User, Group, GroupCurator, GroupMembership, Schedule, Poll
from bot.keyboards.main_menu import get_reply_keyboard
from bot.logger import logger
from aiogram.fsm.context import FSMContext
from bot.handlers.schedule_upload import ScheduleUpload, cancel_kb
from bot.handlers.reports import ReportState
from datetime import datetime

router = Router()

# Вспомогательная функция для получения группы старосты
async def get_starosta_group(session, user_id: int) -> Group | None:
    stmt = select(Group).where(Group.starosta_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().first()

# ==================== ОБРАБОТЧИКИ REPLY‑КНОПОК ====================

@router.message(F.text == "📋 Мои опросы")
async def my_polls_reply(message: types.Message):
    async with async_session() as session:
        user_id = message.from_user.id
        # Активные опросы, отправленные пользователю (есть в poll_messages)
        stmt = (select(Poll, PollMessage).join(PollMessage).where(
            PollMessage.user_id == user_id,
            Poll.status == 'active'
        ))
        results = (await session.execute(stmt)).all()
        if not results:
            await message.answer("Активных опросов нет.")
            return
        for poll, _ in results:
            sched = await session.get(Schedule, poll.schedule_id)
            text = (
                f"📚 *{sched.discipline}* ({sched.type})\n"
                f"🕒 {sched.time_start.strftime('%H:%M')} – {sched.time_end.strftime('%H:%M')}\n"
                f"🏫 {sched.audience or 'нет'}\n"
                f"👨‍🏫 {sched.teacher or 'нет'}"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Присутствую", callback_data=f"poll_{poll.id}_present")],
                [InlineKeyboardButton(text="❌ Отсутствую", callback_data=f"poll_{poll.id}_absent")]
            ])
            await message.answer(text, reply_markup=keyboard)

@router.message(F.text == "📊 История")
async def history_reply(message: types.Message):
    async with async_session() as session:
        user_id = message.from_user.id
        stmt = (select(Poll, PollMessage, Attendance).join(PollMessage).outerjoin(Attendance,
                (Attendance.poll_id == Poll.id) & (Attendance.user_id == user_id))
                .where(PollMessage.user_id == user_id, Poll.status == 'finished'))
        results = (await session.execute(stmt)).all()
        if not results:
            await message.answer("История посещений пуста.")
            return
        history_lines = []
        for poll, _, att in results:
            sched = await session.get(Schedule, poll.schedule_id)
            status = "присутствовал" if att and att.status == 'present' else ("отсутствовал" if att else "не отметился")
            line = f"{sched.date} {sched.discipline}: {status}"
            history_lines.append(line)
        await message.answer("История:\n" + "\n".join(history_lines[-10:]))  # последние 10 записей

# --- Групповые действия (для старосты и админа) ---

@router.message(F.text == "👥 Моя группа")
async def my_group_reply(message: types.Message, state: FSMContext):
    async with async_session() as session:
        # Проверяем, является ли пользователь старостой
        group = await get_starosta_group(session, message.from_user.id)
        if group:
            # Староста – сразу показывает меню группы
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📋 Загрузить список студентов", callback_data="starosta_upload_list")],
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")]
            ])
            await message.answer(f"Управление группой «{group.name}»:", reply_markup=keyboard)
            return

        # Возможно, админ или куратор
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result.scalars().first()
        if user and user.is_admin:
            # Админ – выбор группы
            groups = (await session.execute(select(Group))).scalars().all()
            if not groups:
                await message.answer("Нет доступных групп.")
                return
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=g.name, callback_data=f"mygroup_{g.id}")] for g in groups
            ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
            await message.answer("Выберите группу:", reply_markup=keyboard)
            return

    await message.answer("У вас нет прав для управления группой.")

@router.message(F.text == "📅 Загрузить расписание")
async def upload_schedule_reply(message: types.Message, state: FSMContext):
    async with async_session() as session:
        group = await get_starosta_group(session, message.from_user.id)
        if group:
            # Староста – сразу переходим к загрузке для своей группы
            await state.update_data(group_id=group.id, group_name=group.name)
            await message.answer(
                f"Отправьте Excel-файл с расписанием для группы {group.name}.\n"
                "Ожидаемые столбцы: День недели, Дата, Время с, Время по, Дисциплина, Преподаватель, Аудитория, Группа",
                reply_markup=cancel_kb  # cancel_kb надо импортировать или создать
            )
            await state.set_state(ScheduleUpload.waiting_for_file)
            return

        # Админ
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result.scalars().first()
        if user and user.is_admin:
            groups = (await session.execute(select(Group))).scalars().all()
            if not groups:
                await message.answer("Нет доступных групп.")
                return
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=g.name, callback_data=f"schedgroup_{g.id}")] for g in groups
            ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
            await message.answer("Выберите группу для загрузки расписания:", reply_markup=keyboard)
            return

    await message.answer("У вас нет прав для загрузки расписания.")

@router.message(F.text == "📈 Отчёт")
async def report_reply(message: types.Message, state: FSMContext):
    async with async_session() as session:
        # 1. Если пользователь — староста, сразу запрашиваем даты для его группы
        group = await get_starosta_group(session, message.from_user.id)
        if group:
            await state.update_data(group_id=group.id, report_type="general")
            await message.answer(
                "Введите дату или диапазон дат (ГГГГ-ММ-ДД [ГГГГ-ММ-ДД]):"
            )
            await state.set_state(ReportState.waiting_dates)
            return

        # 2. Если админ — выбор группы
        user = (await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )).scalars().first()
        if user and user.is_admin:
            groups = (await session.execute(select(Group))).scalars().all()
            if not groups:
                await message.answer("Нет доступных групп.")
                return
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=g.name, callback_data=f"reportgroup_{g.id}")] for g in groups
            ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
            await message.answer("Выберите группу для отчёта:", reply_markup=keyboard)
            return

    await message.answer("У вас нет прав на просмотр отчётов.")

@router.message(F.text == "📊 Процент посещаемости")
async def curator_attendance_reply(message: types.Message):
    async with async_session() as session:
        # Куратор
        stmt = select(Group).join(GroupCurator).where(GroupCurator.user_id == message.from_user.id)
        groups = (await session.execute(stmt)).scalars().all()
        if groups:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=g.name, callback_data=f"curatt_{g.id}")] for g in groups
            ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
            await message.answer("Выберите группу для просмотра процента посещаемости:", reply_markup=keyboard)
            return

        # Админ
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result.scalars().first()
        if user and user.is_admin:
            groups = (await session.execute(select(Group))).scalars().all()
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=g.name, callback_data=f"curatt_{g.id}")] for g in groups
            ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
            await message.answer("Выберите группу:", reply_markup=keyboard)
            return

    await message.answer("У вас нет прав для просмотра процента посещаемости.")

@router.message(F.text == "🗑 Удалить расписание")
async def delete_schedule_reply(message: types.Message, state: FSMContext):
    async with async_session() as session:
        user = (await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )).scalars().first()
        if not user:
            await message.answer("Пользователь не найден.")
            return

        # Староста
        group = await get_starosta_group(session, message.from_user.id)
        if group:
            # Удаляем будущие занятия без опросов для своей группы
            today = datetime.now().date()
            await session.execute(
                select(Schedule).where(
                    Schedule.group_id == group.id,
                    Schedule.date >= today,
                    ~Schedule.polls.any()
                ).delete(synchronize_session='fetch')
            )
            await session.commit()
            await message.answer(f"Расписание для группы {group.name} очищено (будущие занятия без опросов удалены).")
            return

        # Админ
        if user.is_admin:
            groups = (await session.execute(select(Group))).scalars().all()
            if not groups:
                await message.answer("Нет доступных групп.")
                return
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=g.name, callback_data=f"delsched_{g.id}")] for g in groups
            ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
            await message.answer("Выберите группу для удаления расписания:", reply_markup=keyboard)
            return

    await message.answer("У вас нет прав для удаления расписания.")

@router.message(F.text == "⚙️ Администрирование")
async def admin_reply(message: types.Message):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result.scalars().first()
        if not user or not user.is_admin:
            await message.answer("Доступ запрещён.")
            return

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Назначить старосту", callback_data="admin_set_starosta")],
        [types.InlineKeyboardButton(text="📌 Назначить куратора", callback_data="admin_set_curator")],
        [types.InlineKeyboardButton(text="👤 Изменить ФИО", callback_data="admin_edit_fullname")],
        [types.InlineKeyboardButton(text="📂 Все группы", callback_data="admin_list_groups")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")],
        [types.InlineKeyboardButton(text="📋 Загрузить список студентов", callback_data="admin_upload_list")],
        [types.InlineKeyboardButton(text="🔓 Отвязать username", callback_data="admin_unlink_username")],
        [types.InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_list_users")],
        [types.InlineKeyboardButton(text="📅 Сегодняшнее расписание", callback_data="admin_schedule_today")],
    ])
    await message.answer("⚙️ Панель администратора", reply_markup=keyboard)