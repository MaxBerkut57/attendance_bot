from aiogram import Bot

bot_instance: Bot | None = None

def set_bot(bot: Bot):
    global bot_instance
    bot_instance = bot

def get_bot() -> Bot:
    if bot_instance is None:
        raise RuntimeError("Bot instance not set")
    return bot_instance