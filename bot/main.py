import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp_socks import ProxyConnector

from bot.config import settings
from bot.logger import logger
from bot.db.database import create_tables, engine

# Простейший роутер для проверки работы
test_router = Router()

@test_router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Я бот учёта посещаемости.")

async def main():
    # Создание таблиц
    try:
        await create_tables()
        logger.info("Таблицы БД созданы")
    except Exception as e:
        logger.error(f"Ошибка создания таблиц: {e}")
        return

    # Настройка прокси (если указан PROXY_URL)
    if settings.PROXY_URL:
        connector = ProxyConnector.from_url(settings.PROXY_URL)
        session = AiohttpSession(connector=connector)
        bot = Bot(token=settings.BOT_TOKEN, session=session)
        logger.info("Используется прокси для Telegram")
    else:
        bot = Bot(token=settings.BOT_TOKEN)

    dp = Dispatcher()
    dp.include_router(test_router)   # подключаем тестовый роутер

    # Включаем логирование входящих обновлений (aiogram)
    # Достаточно установить уровень логгирования aiogram
    import logging
    logging.getLogger("aiogram.event").setLevel(logging.INFO)

    logger.info("Бот запущен, начинаем поллинг...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())