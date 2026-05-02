from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select
from bot.db.models import User, Group, GroupCurator

async def get_main_menu(user: User, session) -> InlineKeyboardMarkup:
    buttons = []

    # Кнопки для всех
    buttons.append([InlineKeyboardButton(text="📋 Мои опросы", callback_data="menu_my_polls")])
    buttons.append([InlineKeyboardButton(text="📊 История", callback_data="menu_history")])

    # Проверяем, является ли пользователь старостой
    stmt_starosta = select(Group).where(Group.starosta_id == user.user_id)
    result_starosta = await session.execute(stmt_starosta)
    starosta_groups = result_starosta.scalars().all()
    if starosta_groups:
        buttons.append([InlineKeyboardButton(text="👥 Моя группа", callback_data="menu_starosta_group")])
        buttons.append([InlineKeyboardButton(text="📅 Загрузить расписание", callback_data="menu_upload_schedule")])
        buttons.append([InlineKeyboardButton(text="📈 Отчёт", callback_data="menu_report")])

    # Проверяем, является ли пользователь куратором (хотя бы одна группа)
    stmt_curator = select(GroupCurator).where(GroupCurator.user_id == user.user_id)
    result_curator = await session.execute(stmt_curator)
    if result_curator.scalars().first():
        buttons.append([InlineKeyboardButton(text="📊 Процент посещаемости (куратор)", callback_data="menu_curator_attendance")])

    # Админ
    if user.is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Администрирование", callback_data="menu_admin")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_reply_keyboard(user: User, session) -> ReplyKeyboardMarkup:
    """Постоянная клавиатура (снизу) с основными разделами."""
    buttons = [
        [KeyboardButton(text="📋 Мои опросы")],
        [KeyboardButton(text="📊 История")],
    ]

    # Староста
    stmt = select(Group).where(Group.starosta_id == user.user_id)
    if (await session.execute(stmt)).scalars().first():
        buttons.append([KeyboardButton(text="👥 Моя группа")])
        buttons.append([KeyboardButton(text="📅 Загрузить расписание")])
        buttons.append([KeyboardButton(text="🗑 Удалить расписание")])
        buttons.append([KeyboardButton(text="📈 Отчёт")])

    # Куратор
    stmt_cur = select(GroupCurator).where(GroupCurator.user_id == user.user_id)
    if (await session.execute(stmt_cur)).scalars().first():
        buttons.append([KeyboardButton(text="📊 Процент посещаемости")])

    # Админ
    if user.is_admin:
        buttons.append([KeyboardButton(text="👥 Моя группа")])
        buttons.append([KeyboardButton(text="📅 Загрузить расписание")])
        buttons.append([KeyboardButton(text="📈 Отчёт")])
        buttons.append([KeyboardButton(text="📊 Процент посещаемости")])
        buttons.append([KeyboardButton(text="🗑 Удалить расписание")])
        buttons.append([KeyboardButton(text="⚙️ Администрирование")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)