"""Support for Freebox devices (Freebox v6 and Freebox mini 4K)."""

from datetime import timedelta

from freebox_api.exceptions import HttpRequestError

from menuai.const import CONF_HOST, CONF_PORT, EVENT_menuai_STOP
from menuai.core import Event, menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.event import async_track_time_interval

from .const import PLATFORMS
from .router import FreeboxConfigEntry, FreeboxRouter, get_api

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(menuai: menuai, entry: FreeboxConfigEntry) -> bool:
    """Set up Freebox entry."""
    api = await get_api(menuai, entry.data[CONF_HOST])
    try:
        await api.open(entry.data[CONF_HOST], entry.data[CONF_PORT])
    except HttpRequestError as err:
        raise ConfigEntryNotReady from err

    freebox_config = await api.system.get_config()

    router = FreeboxRouter(menuai, entry, api, freebox_config)
    await router.update_all()
    entry.async_on_unload(
        async_track_time_interval(menuai, router.update_all, SCAN_INTERVAL)
    )

    entry.runtime_data = router

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_close_connection(event: Event) -> None:
        """Close Freebox connection on HA Stop."""
        await router.close()

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, async_close_connection)
    )
    entry.async_on_unload(router.close)

    return True


async def async_unload_entry(menuai: menuai, entry: FreeboxConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
