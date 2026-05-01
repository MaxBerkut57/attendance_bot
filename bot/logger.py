import logging
import os
import sys
import structlog
from bot.config import settings

def setup_logger():
    if settings.LOG_FILE:
        log_dir = os.path.dirname(settings.LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Удаляем все существующие обработчики (чтобы не было дублирования)
    root_logger.handlers.clear()

    # Форматтер для стандартного вывода
    formatter = logging.Formatter("%(message)s")

    # Консольный обработчик (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(settings.LOG_LEVEL)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Файловый обработчик
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(settings.LOG_LEVEL)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger("aiohttp").setLevel(logging.WARNING)  # чтобы не спамило

setup_logger()
logger = structlog.get_logger()