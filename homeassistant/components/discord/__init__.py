"""The discord integration."""

from aiohttp.client_exceptions import ClientConnectorError
import nextcord

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_TOKEN, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

from .const import DATA_menuai_CONFIG, DOMAIN

PLATFORMS = [Platform.NOTIFY]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Discord component."""

    menuai.data[DATA_menuai_CONFIG] = config
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Discord from a config entry."""
    nextcord.VoiceClient.warn_nacl = False
    discord_bot = nextcord.Client()
    try:
        await discord_bot.login(entry.data[CONF_API_TOKEN])
    except nextcord.LoginFailure as ex:
        raise ConfigEntryAuthFailed("Invalid token given") from ex
    except (ClientConnectorError, nextcord.HTTPException, nextcord.NotFound) as ex:
        raise ConfigEntryNotReady("Failed to connect") from ex
    finally:
        await discord_bot.close()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data

    menuai.async_create_task(
        discovery.async_load_platform(
            menuai, Platform.NOTIFY, DOMAIN, dict(entry.data), menuai.data[DATA_menuai_CONFIG]
        )
    )

    return True
