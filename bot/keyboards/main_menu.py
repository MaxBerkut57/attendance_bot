from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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