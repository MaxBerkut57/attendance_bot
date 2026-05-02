from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta

def generate_calendar(current_date: date, callback_prefix: str) -> InlineKeyboardMarkup:
    """
    Генерирует inline-клавиатуру с днями недели и кнопками переключения недель.
    callback_prefix – префикс для callback_data (например: 'report_date', 'cur_date', 'view_sched')
    """
    monday = current_date - timedelta(days=current_date.weekday())
    sunday = monday + timedelta(days=6)

    day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    header = [InlineKeyboardButton(text=name, callback_data='calendar_ignore') for name in day_names]
    keyboard = [header]

    # Числа
    week_days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        date_str = day.strftime('%Y-%m-%d')
        week_days.append(InlineKeyboardButton(
            text=str(day.day),
            callback_data=f"{callback_prefix}:{date_str}"
        ))
    keyboard.append(week_days)

    # Навигация
    prev_week = monday - timedelta(days=7)
    next_week = monday + timedelta(days=7)
    nav = [
        InlineKeyboardButton(text="⬅️", callback_data=f"cal_shift:{callback_prefix}:{prev_week.isoformat()}"),
        InlineKeyboardButton(text=f"{monday.strftime('%d.%m')} – {sunday.strftime('%d.%m')}", callback_data='calendar_ignore'),
        InlineKeyboardButton(text="➡️", callback_data=f"cal_shift:{callback_prefix}:{next_week.isoformat()}")
    ]
    keyboard.append(nav)

    # Кнопка отмены
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)