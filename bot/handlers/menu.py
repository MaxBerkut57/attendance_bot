from aiogram import Router, types, F
from bot.keyboards.main_menu import get_main_menu
from bot.db.database import async_session
from bot.db.models import User

router = Router()

# # Универсальный обработчик для всех menu_*
# @router.callback_query(F.data.startswith("menu_"))
# async def process_menu(callback: types.CallbackQuery):
#     await callback.answer()
#     action = callback.data
#
#     # if action == "menu_admin":
#     #     return  # обрабатывается в admin.py
#     if action not in ["menu_admin"]:
#         if action == "menu_my_polls":
#             await callback.message.answer("📋 Здесь будут ваши активные опросы (в разработке).")
#         elif action == "menu_history":
#             await callback.message.answer("📊 Здесь будет история посещений (в разработке).")
#         elif action == "menu_starosta_group":
#             await callback.message.answer("👥 Управление группой (в разработке).")
#         elif action == "menu_upload_schedule":
#             await callback.message.answer("📅 Загрузка расписания (в разработке).")
#         elif action == "menu_report":
#             await callback.message.answer("📈 Отчёт о посещаемости (в разработке).")
#         elif action == "menu_curator_attendance":
#             await callback.message.answer("📊 Процент посещаемости группы (в разработке).")
#         # Админские колбэки обрабатываются в admin.py
#         # elif action == "menu_admin":
#         #     # Вызов admin_menu из admin.py, но чтобы не дублировать, перенаправим
#         #     # Можно оставить пустым, т.к. admin.py уже обрабатывает "menu_admin"
#         #     pass
#         else:
#             await callback.message.answer("Неизвестная команда.")

# Обработчики для каждого пункта меню
@router.callback_query(F.data == "menu_my_polls")
async def my_polls(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("📋 Здесь будут ваши активные опросы (в разработке).")

@router.callback_query(F.data == "menu_history")
async def history(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("📊 Здесь будет история посещений (в разработке).")

@router.callback_query(F.data == "menu_starosta_group")
async def starosta_group(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("👥 Управление группой (в разработке).")

# Обработчики для каждого пункта меню
@router.callback_query(F.data == "menu_upload_schedule")
async def upload_schedule(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("📅 Загрузка расписания (в разработке).")

@router.callback_query(F.data == "menu_report")
async def report(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("📈 Отчёт о посещаемости (в разработке).")

@router.callback_query(F.data == "menu_curator_attendance")
async def curator_attendance(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("📊 Процент посещаемости группы (в разработке).")

@router.callback_query(F.data.startswith("menu_"), F.data != "menu_admin")
async def unknown_menu(callback: types.CallbackQuery):
    await callback.answer("Неизвестная команда")
