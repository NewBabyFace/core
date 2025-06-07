"""The GPSD integration."""

from __future__ import annotations

from gps3.agps3threaded import AGPS3mechanism

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PORT, Platform
from menuai.core import menuai

PLATFORMS: list[Platform] = [Platform.SENSOR]

type GPSDConfigEntry = ConfigEntry[AGPS3mechanism]


async def async_setup_entry(menuai: menuai, entry: GPSDConfigEntry) -> bool:
    """Set up GPSD from a config entry."""
    agps_thread = AGPS3mechanism()
    entry.runtime_data = agps_thread

    def setup_agps() -> None:
        host = entry.data.get(CONF_HOST)
        port = entry.data.get(CONF_PORT)
        agps_thread.stream_data(host, port)
        agps_thread.run_thread()

    await menuai.async_add_executor_job(setup_agps)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: GPSDConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        agps_thread = entry.runtime_data
        await menuai.async_add_executor_job(
            lambda: agps_thread.stream_data(
                host=entry.data.get(CONF_HOST),
                port=entry.data.get(CONF_PORT),
                enable=False,
            )
        )

    return unload_ok
