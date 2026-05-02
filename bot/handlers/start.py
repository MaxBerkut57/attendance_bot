from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import User, GroupMembership, Group
from bot.keyboards.main_menu import get_main_menu, get_reply_keyboard
from bot.logger import logger
import re
from bot.db.models import PendingInvite
from sqlalchemy import select

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_user = message.from_user
    user_id = tg_user.id
    username = tg_user.username or None
    full_name = tg_user.full_name

    if message.text and message.text.startswith("/start invite_"):
        token = message.text[13:]
        async with async_session() as session:
            invite = await session.get(PendingInvite, token)
            if not invite:
                await message.answer(
                    "Недействительная ссылка приглашения. Возможно, она уже использована или устарела.")
                return

            # Ищем пользователя по искусственному username
            stmt = select(User).where(User.username == f"invite_{token}")
            result = await session.execute(stmt)
            user = result.scalars().first()
            if not user:
                await message.answer("Ошибка: пользователь не найден. Обратитесь к старосте.")
                return

            # Проверяем, не привязан ли уже этот Telegram ID к другому аккаунту
            existing_user = (await session.execute(
                select(User).where(User.user_id == user_id)
            )).scalars().first()
            if existing_user:
                await message.answer(
                    f"Ваш Telegram аккаунт уже привязан к пользователю «{existing_user.full_name}».\n"
                    "Если хотите привязать другого студента, сначала отвяжите старый аккаунт через администратора."
                )
                return

            # Проверяем, свободен ли username из Telegram (если он есть)
            if username:
                user_with_same_username = (await session.execute(
                    select(User).where(User.username == username)
                )).scalars().first()
                if user_with_same_username and user_with_same_username.id != user.id:
                    await message.answer(
                        "Этот Telegram-username уже используется другим пользователем.\n"
                        "Пожалуйста, смените username в Telegram или обратитесь к администратору."
                    )
                    return

            try:
                user.user_id = user_id
                if username:
                    user.username = username  # заменяем искусственный username на реальный
                # Находим все членства, где этот пользователь есть (по id или по username)
                memberships = await session.execute(
                    select(GroupMembership).where(
                        GroupMembership.user_id.is_(None),
                        GroupMembership.user.has(User.id == user.id)  # ищем по id, а не по username
                    )
                )
                for ms in memberships.scalars():
                    ms.user_id = user_id

                # Удаляем использованный токен
                await session.delete(invite)
                await session.commit()
            except Exception as e:
                logger.error(f"Invite activation failed: {e}")
                await session.rollback()
                await message.answer("Произошла ошибка при активации приглашения. Попробуйте позже.")
                return

            await message.answer(
                f"Добро пожаловать, {user.full_name}! Вы успешно привязаны к системе.",
                reply_markup=await get_reply_keyboard(user, session)
            )
        return


    async with async_session() as session:
        # 1. Ищем пользователя по user_id
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        if user:
            # Обновляем данные (username мог измениться)
            user.username = username
            # user.full_name = full_name
            await session.commit()
            await message.answer(
                f"С возвращением, {user.full_name}!",
                reply_markup= await get_reply_keyboard(user, session)
            )
            logger.info(f"Existing user logged in: {user_id}")
            return

        # 2. Ищем незарегистрированного пользователя по username
        if username:
            stmt = select(User).where(User.username == username, User.user_id.is_(None))
            result = await session.execute(stmt)
            user = result.scalars().first()
            if user:
                # Привязываем Telegram ID
                user.user_id = user_id
                user.full_name = full_name
                # Дополнительно: привязываем к группам, куда он был добавлен заочно
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
                    f"Вы успешно привязаны как {user.full_name}!\n"
                    "Теперь вам будут приходить опросы о посещаемости.",
                    reply_markup= await get_reply_keyboard(user, session)
                )
                logger.info(f"User linked: {username} -> {user_id}")
                return

        # 3. Создаём нового пользователя (без группы)
        if username:
            existing = await session.execute(
                select(User).where(User.username == username)
            )
            if existing.scalars().first():
                await message.answer(
                    "Этот username уже привязан к другому аккаунту Telegram.\n"
                    "Если это ваш аккаунт, обратитесь к администратору для переноса."
                )
                return

        user = User(
            user_id=user_id,
            username=username,
            full_name=full_name,
            is_admin=False
        )
        session.add(user)
        await session.commit()
        await message.answer(
            "Вы зарегистрированы в системе учёта посещаемости.\n"
            "Дождитесь, пока староста добавит вас в группу.",
            reply_markup=await get_reply_keyboard(user, session)
        )
        logger.info(f"New user registered: {user_id}")