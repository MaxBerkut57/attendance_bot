from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta
import calendar

MONTH_NAMES = [
    '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
]

def generate_calendar(current_date: date, callback_prefix: str) -> InlineKeyboardMarkup:
    monday = current_date - timedelta(days=current_date.weekday())
    sunday = monday + timedelta(days=6)

    # Заголовок дней недели (Пн..Вс)
    day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    header = [InlineKeyboardButton(text=name, callback_data='calendar_ignore') for name in day_names]
    keyboard = [header]

    # Числа с названием месяца
    week_days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        date_str = day.strftime('%Y-%m-%d')
        day_text = f"{day.day} {MONTH_NAMES[day.month]}"
        week_days.append(InlineKeyboardButton(
            text=day_text,
            callback_data=f"{callback_prefix}:{date_str}"
        ))
    keyboard.append(week_days)

    # Навигация: стрелки и сегодня
    prev_week = monday - timedelta(days=7)
    next_week = monday + timedelta(days=7)
    today = date.today()
    nav = [
        InlineKeyboardButton(text="⬅️", callback_data=f"cal_shift:{callback_prefix}:{prev_week.isoformat()}"),
        InlineKeyboardButton(text="Сегодня", callback_data=f"cal_shift:{callback_prefix}:{today.isoformat()}"),
        InlineKeyboardButton(text="➡️", callback_data=f"cal_shift:{callback_prefix}:{next_week.isoformat()}")
    ]
    keyboard.append(nav)

    # Отмена
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)