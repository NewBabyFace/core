"""The Radio Browser integration."""

from __future__ import annotations

from aiodns.error import DNSError
from radios import RadioBrowser, RadioBrowserError

from menuai.config_entries import ConfigEntry
from menuai.const import __version__
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

type RadioBrowserConfigEntry = ConfigEntry[RadioBrowser]


async def async_setup_entry(
    menuai: menuai, entry: RadioBrowserConfigEntry
) -> bool:
    """Set up Radio Browser from a config entry.

    This integration doesn't set up any entities, as it provides a media source
    only.
    """
    session = async_get_clientsession(menuai)
    radios = RadioBrowser(session=session, user_agent=f"menuai/{__version__}")

    try:
        await radios.stats()
    except (DNSError, RadioBrowserError) as err:
        raise ConfigEntryNotReady("Could not connect to Radio Browser API") from err

    entry.runtime_data = radios
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
