"""The devolo_home_control integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from functools import partial
from typing import Any

from devolo_home_control_api.exceptions.gateway import GatewayOfflineError
from devolo_home_control_api.homecontrol import HomeControl
from devolo_home_control_api.mydevolo import Mydevolo

from menuai.components import zeroconf
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME, EVENT_menuai_STOP
from menuai.core import Event, menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers.device_registry import DeviceEntry

from .const import GATEWAY_SERIAL_PATTERN, PLATFORMS

type DevoloHomeControlConfigEntry = ConfigEntry[list[HomeControl]]


async def async_setup_entry(
    menuai: menuai, entry: DevoloHomeControlConfigEntry
) -> bool:
    """Set up the devolo account from a config entry."""
    mydevolo = configure_mydevolo(entry.data)

    credentials_valid = await menuai.async_add_executor_job(mydevolo.credentials_valid)

    if not credentials_valid:
        raise ConfigEntryAuthFailed

    if await menuai.async_add_executor_job(mydevolo.maintenance):
        raise ConfigEntryNotReady

    gateway_ids = await menuai.async_add_executor_job(mydevolo.get_gateway_ids)

    if entry.unique_id and GATEWAY_SERIAL_PATTERN.match(entry.unique_id):
        uuid = await menuai.async_add_executor_job(mydevolo.uuid)
        menuai.config_entries.async_update_entry(entry, unique_id=uuid)

    def shutdown(event: Event) -> None:
        for gateway in entry.runtime_data:
            gateway.websocket_disconnect(
                f"websocket disconnect requested by {EVENT_menuai_STOP}"
            )

    # Listen when EVENT_menuai_STOP is fired
    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, shutdown)
    )

    try:
        zeroconf_instance = await zeroconf.async_get_instance(menuai)
        entry.runtime_data = []
        for gateway_id in gateway_ids:
            entry.runtime_data.append(
                await menuai.async_add_executor_job(
                    partial(
                        HomeControl,
                        gateway_id=str(gateway_id),
                        mydevolo_instance=mydevolo,
                        zeroconf_instance=zeroconf_instance,
                    )
                )
            )
    except GatewayOfflineError as err:
        raise ConfigEntryNotReady from err

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: DevoloHomeControlConfigEntry
) -> bool:
    """Unload a config entry."""
    unload = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    await asyncio.gather(
        *(
            menuai.async_add_executor_job(gateway.websocket_disconnect)
            for gateway in entry.runtime_data
        )
    )
    return unload


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    return True


def configure_mydevolo(conf: Mapping[str, Any]) -> Mydevolo:
    """Configure mydevolo."""
    mydevolo = Mydevolo()
    mydevolo.user = conf[CONF_USERNAME]
    mydevolo.password = conf[CONF_PASSWORD]
    return mydevolo
