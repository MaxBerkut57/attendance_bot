from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import User
from bot.keyboards.main_menu import get_reply_keyboard

router = Router()

# ==================== ОБРАБОТЧИКИ REPLY‑КНОПОК ====================

@router.message(F.text == "📋 Мои опросы")
async def my_polls_reply(message: types.Message):
    await message.answer("📋 Здесь будут ваши активные опросы (в разработке).")

@router.message(F.text == "📊 История")
async def history_reply(message: types.Message):
    await message.answer("📊 Здесь будет история посещений (в разработке).")

@router.message(F.text == "👥 Моя группа")
async def starosta_group_reply(message: types.Message):
    await message.answer("👥 Управление группой (в разработке).")

@router.message(F.text == "📅 Загрузить расписание")
async def upload_schedule_reply(message: types.Message):
    # Позже этот обработчик заменится реальной логикой из schedule_upload.py
    await message.answer("📅 Загрузка расписания (в разработке).")

@router.message(F.text == "📈 Отчёт")
async def report_reply(message: types.Message):
    await message.answer("📈 Отчёт о посещаемости (в разработке).")

@router.message(F.text == "📊 Процент посещаемости")
async def curator_attendance_reply(message: types.Message):
    await message.answer("📊 Процент посещаемости группы (в разработке).")

@router.message(F.text == "⚙️ Администрирование")
async def admin_reply(message: types.Message):
    # Проверяем, является ли пользователь админом
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result.scalars().first()
        if not user or not user.is_admin:
            await message.answer("Доступ запрещён.")
            return

    # Клавиатура администратора (такая же, как в admin.py)
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Назначить старосту", callback_data="admin_set_starosta")],
        [types.InlineKeyboardButton(text="📌 Назначить куратора", callback_data="admin_set_curator")],
        [types.InlineKeyboardButton(text="👤 Изменить ФИО", callback_data="admin_edit_fullname")],
        [types.InlineKeyboardButton(text="📂 Все группы", callback_data="admin_list_groups")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")],
        [types.InlineKeyboardButton(text="📋 Загрузить список студентов", callback_data="admin_upload_list")],
        [types.InlineKeyboardButton(text="🔓 Отвязать username", callback_data="admin_unlink_username")],
        [types.InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_list_users")],
    ])
    await message.answer("⚙️ Панель администратора", reply_markup=keyboard)

# ==================== СТАРЫЕ INLINE‑ОБРАБОТЧИКИ (если нужны) ====================
# Эти обработчики можно оставить для совместимости, но теперь они необязательны.
# Если они конфликтуют, можно удалить.