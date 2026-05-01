# bot/main.py
import asyncio
from aiogram import Bot, Dispatcher
from bot.config import settings
from bot.logger import logger
from bot.db.database import create_tables, engine

async def main():
    await create_tables()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    # Здесь позже подключим роутеры

    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())