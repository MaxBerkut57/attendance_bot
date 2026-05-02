from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from bot.config import settings
from bot.logger import logger
from aiogram import Bot                     # <-- добавлен импорт
from bot.services.poll_service import check_upcoming_lessons, close_expired_polls
import functools

jobstores = {
    'default': RedisJobStore(url=settings.REDIS_URL)
}

scheduler = AsyncIOScheduler(jobstores=jobstores, timezone='Europe/Moscow')

async def start_scheduler(bot: Bot):
    """Запуск планировщика."""
    # Передаём bot в функцию проверки уроков
    check_job = functools.partial(check_upcoming_lessons, bot=bot)
    scheduler.add_job(check_job, 'interval', seconds=60, id='check_lessons')
    scheduler.add_job(close_expired_polls, 'cron', hour=0, minute=5, id='close_polls')
    scheduler.start()
    logger.info("Scheduler started")