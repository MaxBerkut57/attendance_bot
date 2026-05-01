from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import User, Group, GroupCurator, GroupMembership
from bot.keyboards.main_menu import get_main_menu
from bot.logger import logger

router = Router()

cancel_kb = types.InlineKeyboardMarkup(
    inline_keyboard=[[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]]
)

class AdminActions(StatesGroup):
    waiting_username_starosta = State()
    waiting_group_starosta = State()
    waiting_username_curator = State()
    waiting_group_curator = State()
    waiting_username_editfn = State()
    waiting_new_fullname = State()
    waiting_username_unlink = State()

async def find_user_by_username(session, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalars().first()

@router.callback_query(F.data == "admin_unlink_username")
async def start_unlink_username(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите username, который нужно отвязать (без @):", reply_markup=cancel_kb)
    await state.set_state(AdminActions.waiting_username_unlink)
    await callback.answer()

@router.message(StateFilter(AdminActions.waiting_username_unlink))
async def process_unlink_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    async with async_session() as session:
        user = await find_user_by_username(session, username)
        if not user:
            await message.answer("Пользователь с таким username не найден.")
            await state.clear()
            return
        # Отвязываем: сбрасываем user_id
        user.user_id = None
        # Удаляем все членства в группах, где он был как студент (опционально)
        # Лучше просто оставить, чтобы при повторной привязке они восстановились.
        await session.commit()
        logger.info(f"Username unlinked: {username}")
        await message.answer(f"Username @{username} успешно отвязан. Теперь его можно привязать к новому Telegram ID.")
    await state.clear()

# ==================== МЕНЮ АДМИНИСТРИРОВАНИЯ ====================
@router.callback_query(F.data == "menu_admin")
async def admin_menu(callback: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Назначить старосту", callback_data="admin_set_starosta")],
        [types.InlineKeyboardButton(text="📌 Назначить куратора", callback_data="admin_set_curator")],
        [types.InlineKeyboardButton(text="👤 Изменить ФИО", callback_data="admin_edit_fullname")],
        [types.InlineKeyboardButton(text="📂 Все группы", callback_data="admin_list_groups")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")],
        [types.InlineKeyboardButton(text="📋 Загрузить список студентов", callback_data="admin_upload_list")],
        [types.InlineKeyboardButton(text="🔓 Отвязать username", callback_data="admin_unlink_username")],
    ])
    await callback.message.edit_text("⚙️ Панель администратора", reply_markup=keyboard)
    await callback.answer()

# ==================== НАЗНАЧЕНИЕ СТАРОСТЫ ====================
@router.callback_query(F.data == "admin_set_starosta")
async def start_set_starosta(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        groups = (await session.execute(select(Group))).scalars().all()
        if not groups:
            await callback.message.answer("Нет групп для назначения старосты.")
            await callback.answer()
            return
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=g.name, callback_data=f"stargroup_{g.id}")] for g in groups
        ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
    await callback.message.answer("Выберите группу для назначения старосты:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("stargroup_"))
async def choose_group_for_starosta(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[1])
    await state.update_data(group_id=group_id)
    await callback.message.answer("Введите username нового старосты (без @):", reply_markup=cancel_kb)
    await state.set_state(AdminActions.waiting_username_starosta)
    await callback.answer()

@router.message(StateFilter(AdminActions.waiting_username_starosta))
async def process_starosta_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    async with async_session() as session:
        user = await find_user_by_username(session, username)
        if not user:
            await message.answer("Пользователь с таким username не найден в боте. Попробуйте ещё раз.")
            return
        data = await state.get_data()
        group_id = data["group_id"]
        group = await session.get(Group, group_id)
        if not group:
            await message.answer("Группа не найдена.")
            await state.clear()
            return
        group.starosta_id = user.user_id

        # Проверяем наличие членства в группе
        existing = await session.execute(
            select(GroupMembership).where(
                GroupMembership.user_id == user.user_id,
                GroupMembership.group_id == group.id
            )
        )
        if not existing.scalars().first():
            session.add(GroupMembership(user_id=user.user_id, group_id=group.id))

        await session.commit()
        logger.info(f"Starosta set: {username} for group {group.name}")
        await message.answer(f"Пользователь @{username} назначен старостой группы {group.name}.")
        await state.clear()

# ==================== НАЗНАЧЕНИЕ КУРАТОРА ====================
@router.callback_query(F.data == "admin_set_curator")
async def start_set_curator(callback: types.CallbackQuery, state: FSMContext):
    async with async_session() as session:
        groups = (await session.execute(select(Group))).scalars().all()
        if not groups:
            await callback.message.answer("Нет групп для назначения куратора.")
            await callback.answer()
            return
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=g.name, callback_data=f"curgroup_{g.id}")] for g in groups
        ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
    await callback.message.answer("Выберите группу:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("curgroup_"))
async def choose_group_for_curator(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[1])
    await state.update_data(group_id=group_id)
    await callback.message.answer("Введите username куратора (без @):", reply_markup=cancel_kb)
    await state.set_state(AdminActions.waiting_username_curator)
    await callback.answer()

@router.message(StateFilter(AdminActions.waiting_username_curator))
async def process_curator_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    async with async_session() as session:
        user = await find_user_by_username(session, username)
        if not user:
            await message.answer("Пользователь не найден.")
            return
        data = await state.get_data()
        group_id = data["group_id"]
        group = await session.get(Group, group_id)
        if not group:
            await message.answer("Группа не найдена.")
            await state.clear()
            return

        existing = await session.execute(
            select(GroupCurator).where(
                GroupCurator.group_id == group.id,
                GroupCurator.user_id == user.user_id
            )
        )
        if existing.scalars().first():
            await message.answer(f"Пользователь @{username} уже является куратором этой группы.")
        else:
            session.add(GroupCurator(group_id=group.id, user_id=user.user_id))
            await session.commit()
            logger.info(f"Curator added: {username} for group {group.name}")
            await message.answer(f"Пользователь @{username} назначен куратором группы {group.name}.")
        await state.clear()

# ==================== ИЗМЕНЕНИЕ ФИО ====================
@router.callback_query(F.data == "admin_edit_fullname")
async def start_edit_fullname(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите username пользователя (без @):", reply_markup=cancel_kb)
    await state.set_state(AdminActions.waiting_username_editfn)
    await callback.answer()

@router.message(StateFilter(AdminActions.waiting_username_editfn))
async def process_username_editfn(message: types.Message, state: FSMContext):
    username = message.text.strip()
    async with async_session() as session:
        user = await find_user_by_username(session, username)
        if not user:
            await message.answer("Пользователь не найден.")
            return
        await state.update_data(edit_user_id=user.user_id, edit_username=username)
    await message.answer(f"Введите новое ФИО для @{username}:")
    await state.set_state(AdminActions.waiting_new_fullname)

@router.message(StateFilter(AdminActions.waiting_new_fullname))
async def process_new_fullname(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    user_id = data["edit_user_id"]
    username = data["edit_username"]
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return
        user.full_name = new_name
        await session.commit()
        logger.info(f"Changed full_name for {user_id} to '{new_name}'")
    await message.answer(f"ФИО пользователя @{username} изменено на «{new_name}»")
    await state.clear()

# ==================== ВСЕ ГРУППЫ ====================
@router.callback_query(F.data == "admin_list_groups")
async def list_groups(callback: types.CallbackQuery):
    async with async_session() as session:
        groups = (await session.execute(select(Group))).scalars().all()
        if groups:
            text = "Список групп:\n" + "\n".join(f"{g.name} (ID:{g.id})" for g in groups)
        else:
            text = "Группы отсутствуют."
    await callback.message.answer(text)
    await callback.answer()

# ==================== НАЗАД В ГЛАВНОЕ МЕНЮ ====================
@router.callback_query(F.data == "menu_back")
async def back_to_main(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == callback.from_user.id))
        user = result.scalars().first()
        if user:
            await callback.message.edit_text("Главное меню", reply_markup=await get_main_menu(user, session))
    await callback.answer()

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    # Вернём главное меню
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == callback.from_user.id))
        user = result.scalars().first()
        if user:
            await callback.message.answer(
                "Главное меню",
                reply_markup=await get_main_menu(user, session)
            )
    await callback.answer()