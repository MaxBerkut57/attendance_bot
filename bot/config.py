from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str  # asyncpg, например postgresql+asyncpg://user:pass@localhost/attendance
    REDIS_URL: str     # например redis://localhost:6379/0

    # ID администратора (твой)
    ADMIN_USER_ID: int
    ADMIN_USERNAME: str = "pretti_lim"
    ADMIN_FULL_NAME: str = "Латыпов Эмиль Ильнурович"
    ADMIN_GROUP_NAME: str = "ТРИС-1-25"

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/bot.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()