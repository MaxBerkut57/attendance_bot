from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import User, Group, GroupMembership
from bot.keyboards.main_menu import get_reply_keyboard
from bot.logger import logger
from aiogram.fsm.context import FSMContext
from bot.handlers.schedule_upload import ScheduleUpload, cancel_kb
from bot.handlers.reports import ReportStates

router = Router()

# Вспомогательная функция для получения группы старосты
async def get_starosta_group(session, user_id: int) -> Group | None:
    stmt = select(Group).where(Group.starosta_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().first()

# ==================== ОБРАБОТЧИКИ REPLY‑КНОПОК ====================

@router.message(F.text == "📋 Мои опросы")
async def my_polls_reply(message: types.Message):
    # Здесь будет логика показа активных опросов студента
    await message.answer("📋 Здесь будут ваши активные опросы (в разработке).")

@router.message(F.text == "📊 История")
async def history_reply(message: types.Message):
    await message.answer("📊 Здесь будет история посещений (в разработке).")

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
            await state.set_state(ReportStates.waiting_dates)
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
        if not user or not user.is_admin:
            await message.answer("Доступ запрещён.")
            return
        groups = (await session.execute(select(Group))).scalars().all()
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=g.name, callback_data=f"delsched_{g.id}")] for g in groups
        ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
        await message.answer("Выберите группу для удаления расписания:", reply_markup=keyboard)

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