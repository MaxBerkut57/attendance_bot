import logging
import os
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
        logger_factory=structlog.stdlib.LoggerFactory(),  # Теперь совместимо с filter_by_level
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Настройка файлового обработчика
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(settings.LOG_LEVEL)
        root_logger = logging.getLogger()
        root_logger.setLevel(settings.LOG_LEVEL)
        root_logger.addHandler(file_handler)

    # Уровень корневого логгера
    logging.getLogger().setLevel(settings.LOG_LEVEL)

setup_logger()
logger = structlog.get_logger()