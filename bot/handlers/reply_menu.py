from aiogram import Router, types, F

router = Router()

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