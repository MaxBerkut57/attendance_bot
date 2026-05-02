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

    if message.text and message.text.startswith("/start invite_"):
        token = message.text[13:]
        async with async_session() as session:
            invite = await session.get(PendingInvite, token)
            if not invite:
                await message.answer("Недействительная ссылка приглашения.")
                return
            stmt = select(User).where(User.username == f"invite_{token}")
            result = await session.execute(stmt)
            user = result.scalars().first()
            if not user:
                await message.answer("Ошибка: пользователь не найден.")
                return
            user.user_id = user_id
            if username:
                user.username = username
            memberships = await session.execute(
                select(GroupMembership).where(
                    GroupMembership.user_id.is_(None),
                    GroupMembership.user.has(User.username == f"invite_{token}")
                )
            )
            for ms in memberships.scalars():
                ms.user_id = user_id
            await session.delete(invite)
            await session.commit()
            await message.answer(
                f"Добро пожаловать, {user.full_name}! Вы успешно привязаны к системе.",
                reply_markup=await get_reply_keyboard(user, session)
            )
            return

    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        if user:
            user.username = username
            await session.commit()
            await message.answer(
                f"С возвращением, {user.full_name}!",
                reply_markup=await get_reply_keyboard(user, session)
            )
            return

        if username:
            stmt = select(User).where(User.username == username, User.user_id.is_(None))
            result = await session.execute(stmt)
            user = result.scalars().first()
            if user:
                user.user_id = user_id
                user.full_name = full_name
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
                    f"Вы успешно привязаны как {user.full_name}!",
                    reply_markup=await get_reply_keyboard(user, session)
                )
                return

            existing = await session.execute(
                select(User).where(User.username == username)
            )
            if existing.scalars().first():
                await message.answer("Этот username уже занят.")
                return

        user = User(user_id=user_id, username=username, full_name=full_name)
        session.add(user)
        await session.commit()
        await message.answer(
            "Вы зарегистрированы. Дождитесь добавления в группу.",
            reply_markup=await get_reply_keyboard(user, session)
        )