import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from bot.config import settings
from bot.logger import logger
from bot.db.database import create_tables, engine

class ProxiedAiohttpSession(AiohttpSession):
    def __init__(self, proxy_url: str, **kwargs):
        self._proxy_url = proxy_url
        super().__init__(**kwargs)

    async def create_session(self, **kwargs):
        connector = ProxyConnector.from_url(self._proxy_url)
        return aiohttp.ClientSession(connector=connector, **kwargs)

async def main():
    await create_tables()

    if settings.PROXY_URL:
        session = ProxiedAiohttpSession(proxy_url=settings.PROXY_URL)
        bot = Bot(token=settings.BOT_TOKEN, session=session)
        logger.info("Using SOCKS5 proxy for Telegram API")
    else:
        bot = Bot(token=settings.BOT_TOKEN)

    dp = Dispatcher()
    print("=== Bot started (print) ===")
    logger.info("Bot started")

    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())