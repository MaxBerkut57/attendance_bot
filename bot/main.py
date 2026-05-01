import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from bot.config import settings
from bot.logger import logger
from bot.db.database import create_tables, engine

async def main():
    await create_tables()

    if settings.PROXY_URL:
        connector = ProxyConnector.from_url(settings.PROXY_URL)
        client_session = aiohttp.ClientSession(connector=connector)
        tg_session = AiohttpSession(session=client_session)
        bot = Bot(token=settings.BOT_TOKEN, session=tg_session)
        logger.info("Using SOCKS5 proxy for Telegram API")
    else:
        bot = Bot(token=settings.BOT_TOKEN)

    dp = Dispatcher()
    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())