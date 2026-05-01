from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.db.models import User

def get_main_menu(user: User) -> InlineKeyboardMarkup:
    """Генерация главного меню в зависимости от роли."""
    buttons = []

    # Общие для всех
    buttons.append([InlineKeyboardButton(text="📋 Мои опросы", callback_data="menu_my_polls")])
    buttons.append([InlineKeyboardButton(text="📊 История", callback_data="menu_history")])

    # Староста
    # Проверим, является ли пользователь старостой хоть одной группы
    if user.user_id:
        from bot.db.models import Group
        # Потребуется запрос к БД, поэтому можно принимать флаг в функции,
        # но для простоты будем передавать дополнительные данные.
        # На данном этапе сделаем заглушку: добавим кнопку "Моя группа", если есть хоть одна группа, где пользователь староста.
        # Передадим это через дополнительный параметр позже.
        pass  # Временно не проверяем, но можно оставить заглушки.

    # Куратор
    # Админ
    if user.is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Администрирование", callback_data="menu_admin")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard