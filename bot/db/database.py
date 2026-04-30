from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from bot.config import settings
from bot.db.base import Base
from bot.logger import logger

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")

async def get_session():
    async with async_session() as session:
        yield session