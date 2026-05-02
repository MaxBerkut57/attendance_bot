from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from bot.config import settings
from bot.logger import logger
from aiogram import Bot
from bot.services.poll_service import check_upcoming_lessons, close_expired_polls
import functools
import redis as sync_redis          # синхронный клиент для APScheduler

# Создаём Redis-клиент синхронно (APScheduler использует синхронный redis внутри)
redis_client = sync_redis.Redis.from_url(settings.REDIS_URL)

jobstores = {
    'default': RedisJobStore(redis=redis_client)
}

scheduler = AsyncIOScheduler(jobstores=jobstores, timezone='Europe/Moscow')

async def start_scheduler(bot: Bot):
    check_job = functools.partial(check_upcoming_lessons, bot=bot)
    scheduler.add_job(check_job, 'interval', seconds=60, id='check_lessons')
    scheduler.add_job(close_expired_polls, 'cron', hour=0, minute=5, id='close_polls')
    scheduler.start()
    logger.info("Scheduler started")