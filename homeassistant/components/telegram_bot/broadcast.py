"""Support for Telegram bot to send messages only."""

from telegram import Bot

from menuai.core import menuai

from .bot import BaseTelegramBot, TelegramBotConfigEntry


async def async_setup_platform(
    menuai: menuai, bot: Bot, config: TelegramBotConfigEntry
) -> type[BaseTelegramBot] | None:
    """Set up the Telegram broadcast platform."""
    return None
