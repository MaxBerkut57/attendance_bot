from aiogram import Router, types

router = Router()

@router.callback_query(lambda c: c.data and c.data.startswith("menu_"))
async def process_menu(callback: types.CallbackQuery):
    await callback.answer()
    action = callback.data
    if action == "menu_my_polls":
        await callback.message.answer("Раздел в разработке")
    elif action == "menu_history":
        await callback.message.answer("Раздел в разработке")
    elif action == "menu_admin":
        await callback.message.answer("Панель администратора в разработке")
    else:
        await callback.message.answer("Неизвестная команда")