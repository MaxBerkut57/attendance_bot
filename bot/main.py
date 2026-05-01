import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp_socks import ProxyConnector

from bot.config import settings
from bot.logger import logger
from bot.db.database import create_tables, engine

async def main():
    await create_tables()

    # Настройка SOCKS5-прокси для Telegram
    if settings.PROXY_URL:
        connector = ProxyConnector.from_url(settings.PROXY_URL)
        session = AiohttpSession(connector=connector)
        bot = Bot(token=settings.BOT_TOKEN, session=session)
        logger.info("Using SOCKS5 proxy for Telegram API")
    else:
        bot = Bot(token=settings.BOT_TOKEN)

    dp = Dispatcher()
    # Здесь позже добавим роутеры

    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())