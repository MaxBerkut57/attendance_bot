from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import User, GroupMembership, Group, PendingInvite
from bot.keyboards.main_menu import get_main_menu, get_reply_keyboard
from bot.logger import logger

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_user = message.from_user
    user_id = tg_user.id
    username = tg_user.username or None
    full_name = tg_user.full_name

    # ========== Обработка инвайт-ссылки ==========
    if message.text and message.text.startswith("/start invite_"):
        token = message.text[13:]
        async with async_session() as session:
            invite = await session.get(PendingInvite, token)
            if not invite:
                await message.answer("Недействительная ссылка приглашения.")
                return
            # Находим пользователя по искусственному username
            stmt = select(User).where(User.username == f"invite_{token}")
            result = await session.execute(stmt)
            user = result.scalars().first()
            if not user:
                await message.answer("Ошибка: пользователь не найден.")
                return

            # Проверка: не привязан ли уже этот Telegram ID
            existing_user = (await session.execute(
                select(User).where(User.user_id == user_id)
            )).scalars().first()
            if existing_user:
                await message.answer("Ваш Telegram аккаунт уже привязан к другому пользователю.")
                return

            # Проверка на конфликт username (если в Telegram есть username)
            if username:
                same_username = (await session.execute(
                    select(User).where(User.username == username)
                )).scalars().first()
                if same_username and same_username.id != user.id:
                    await message.answer("Этот Telegram-username уже занят другим студентом.")
                    return

            # 1. Обновляем членство в группе (находим по invite-username)
            memberships = await session.execute(
                select(GroupMembership).where(
                    GroupMembership.user_id.is_(None),
                    GroupMembership.user.has(User.username == f"invite_{token}")
                )
            )
            for ms in memberships.scalars():
                ms.user_id = user_id   # проставляем Telegram ID

            # 2. Привязываем Telegram ID и, если возможно, обновляем username
            user.user_id = user_id
            if username:
                user.username = username
            # 3. Удаляем использованный токен
            await session.delete(invite)
            await session.commit()

            await message.answer(
                f"Добро пожаловать, {user.full_name}! Вы успешно привязаны к системе.",
                reply_markup=await get_reply_keyboard(user, session)
            )
            return

    # ========== Обычный вход ==========
    async with async_session() as session:
        # 1. Пользователь уже зарегистрирован (есть Telegram ID)
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        if user:
            user.username = username   # обновляем username, если изменился
            await session.commit()
            await message.answer(
                f"С возвращением, {user.full_name}!",
                reply_markup=await get_reply_keyboard(user, session)
            )
            logger.info(f"Existing user logged in: {user_id}")
            return

        # 2. Пользователь был загружен списком, но ещё не привязан (есть username, но user_id IS NULL)
        if username:
            stmt = select(User).where(User.username == username, User.user_id.is_(None))
            result = await session.execute(stmt)
            user = result.scalars().first()
            if user:
                # Привязываем Telegram ID, имя НЕ трогаем
                user.user_id = user_id
                # Находим все членства, где он есть, и проставляем Telegram ID
                memberships = await session.execute(
                    select(GroupMembership).where(
                        GroupMembership.user_id.is_(None),
                        GroupMembership.user.has(User.username == username)
                    )
                )
                for ms in memberships.scalars():
                    ms.user_id = user_id

                await session.commit()
                await message.answer(
                    f"Вы успешно привязаны как {user.full_name}!\nТеперь вам будут приходить опросы.",
                    reply_markup=await get_reply_keyboard(user, session)
                )
                logger.info(f"User linked: {username} -> {user_id}")
                return

        # 3. Проверка на занятость username (для нового пользователя)
        if username:
            existing = await session.execute(
                select(User).where(User.username == username)
            )
            if existing.scalars().first():
                await message.answer("Этот username уже занят. Если это ваш аккаунт, обратитесь к администратору.")
                return

        # 4. Полностью новый пользователь
        user = User(
            user_id=user_id,
            username=username,
            full_name=full_name,
            is_admin=False
        )
        session.add(user)
        await session.commit()
        await message.answer(
            "Вы зарегистрированы в системе учёта посещаемости.\nДождитесь, пока староста добавит вас в группу.",
            reply_markup=await get_reply_keyboard(user, session)
        )
        logger.info(f"New user registered: {user_id}")