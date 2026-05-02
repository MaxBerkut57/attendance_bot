from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from bot.config import settings
from bot.logger import logger
from aiogram import Bot
from bot.services.poll_service import check_upcoming_lessons, close_expired_polls
from urllib.parse import urlparse

# Парсим REDIS_URL
parsed = urlparse(settings.REDIS_URL)
redis_host = parsed.hostname or 'localhost'
redis_port = parsed.port or 6379
redis_db = 0
if parsed.path:
    try:
        redis_db = int(parsed.path.strip('/'))
    except ValueError:
        pass
redis_password = parsed.password

jobstores = {
    'default': RedisJobStore(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password
    )
}

scheduler = AsyncIOScheduler(jobstores=jobstores, timezone='Europe/Moscow')

async def start_scheduler(bot: Bot):
    scheduler.add_job(
        check_upcoming_lessons,
        'interval',
        seconds=60,
        id='check_lessons',
        kwargs={'bot': bot}
    )
    scheduler.add_job(
        close_expired_polls,
        'cron',
        hour=0,
        minute=5,
        id='close_polls'
    )
    scheduler.start()
    logger.info("Scheduler started")