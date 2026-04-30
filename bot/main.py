import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from bot.config import settings
from bot.config import settings
from bot.logger import logger
from bot.db.database import create_tables
from bot.db.database import engine

async def main():
    # Создание таблиц
    await create_tables()

    if settings.PROXY_URL:
        from aiohttp_socks import ProxyConnector
        from aiogram.client.session.aiohttp import AiohttpSession
        connector = ProxyConnector.from_url(settings.PROXY_URL)
        session = AiohttpSession(connector=connector)
        bot = Bot(token=settings.BOT_TOKEN, session=session)
        logger.info("Using SOCKS5 proxy for Telegram")
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

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())