import asyncio
from aiogram import Bot, Dispatcher
from bot.config import settings
from bot.logger import logger
from bot.db.database import create_tables, engine

async def main():
    # Создание таблиц в БД
    await create_tables()

    # Создаём бота с поддержкой SOCKS5-прокси
    if settings.PROXY_URL:
        bot = Bot(token=settings.BOT_TOKEN, proxy=settings.PROXY_URL)
        logger.info("Using proxy for Telegram API")
    else:
        bot = Bot(token=settings.BOT_TOKEN)

    dp = Dispatcher()
    # Здесь будут регистрироваться роутеры

    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())