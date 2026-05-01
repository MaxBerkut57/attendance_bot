from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from bot.config import settings
from bot.db.base import Base
from bot.db.models import User, Group, GroupMembership
from bot.logger import logger
from sqlalchemy import select

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")

async def get_session():
    async with async_session() as session:
        yield session

async def seed_admin():
    """Создать или обновить администратора и его группу."""
    async with async_session() as session:
        # Создаём группу, если её нет
        group = await session.scalar(
            select(Group).where(Group.name == settings.ADMIN_GROUP_NAME)
        )
        if not group:
            group = Group(name=settings.ADMIN_GROUP_NAME)
            session.add(group)
            await session.flush()
            logger.info(f"Created group {settings.ADMIN_GROUP_NAME}")

        # Создаём пользователя-админа
        admin_user = (
            await session.execute(select(User).where(User.user_id == settings.ADMIN_USER_ID))).scalars().first()
        if not admin_user:
            admin_user = User(
                user_id=settings.ADMIN_USER_ID,
                username=settings.ADMIN_USERNAME,
                full_name=settings.ADMIN_FULL_NAME,
                is_admin=True
            )
            session.add(admin_user)
            logger.info(f"Created admin user {settings.ADMIN_USER_ID}")
        else:
            # Обновляем данные на случай изменения
            admin_user.username = settings.ADMIN_USERNAME
            admin_user.full_name = settings.ADMIN_FULL_NAME
            admin_user.is_admin = True

        # Добавляем в группу
        membership = await session.scalar(
            select(GroupMembership).where(
                GroupMembership.user_id == admin_user.user_id,
                GroupMembership.group_id == group.id
            )
        )
        if not membership:
            session.add(GroupMembership(user_id=admin_user.user_id, group_id=group.id))
            logger.info(f"Added admin to group {group.name}")

        await session.commit()