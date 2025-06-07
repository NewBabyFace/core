"""The motion_blinds component."""

import asyncio
import logging
from typing import TYPE_CHECKING

from motionblinds import AsyncMotionMulticast

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, CONF_HOST, EVENT_menuai_STOP
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import (
    CONF_BLIND_TYPE_LIST,
    CONF_INTERFACE,
    CONF_WAIT_FOR_PUSH,
    DEFAULT_INTERFACE,
    DEFAULT_WAIT_FOR_PUSH,
    DOMAIN,
    KEY_API_LOCK,
    KEY_COORDINATOR,
    KEY_GATEWAY,
    KEY_MULTICAST_LISTENER,
    KEY_SETUP_LOCK,
    KEY_UNSUB_STOP,
    PLATFORMS,
)
from .coordinator import DataUpdateCoordinatorMotionBlinds
from .gateway import ConnectMotionGateway

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up the motion_blinds components from a config entry."""
    menuai.data.setdefault(DOMAIN, {})
    setup_lock = menuai.data[DOMAIN].setdefault(KEY_SETUP_LOCK, asyncio.Lock())
    host = entry.data[CONF_HOST]
    key = entry.data[CONF_API_KEY]
    multicast_interface = entry.data.get(CONF_INTERFACE, DEFAULT_INTERFACE)
    wait_for_push = entry.options.get(CONF_WAIT_FOR_PUSH, DEFAULT_WAIT_FOR_PUSH)
    blind_type_list = entry.data.get(CONF_BLIND_TYPE_LIST)

    # Create multicast Listener
    async with setup_lock:
        if KEY_MULTICAST_LISTENER not in menuai.data[DOMAIN]:
            # check multicast interface
            check_multicast_class = ConnectMotionGateway(
                menuai, interface=multicast_interface
            )
            working_interface = await check_multicast_class.async_check_interface(
                host, key
            )
            if working_interface != multicast_interface:
                data = {**entry.data, CONF_INTERFACE: working_interface}
                menuai.config_entries.async_update_entry(entry, data=data)
                _LOGGER.debug(
                    (
                        "Motionblinds interface updated from %s to %s, "
                        "this should only occur after a network change"
                    ),
                    multicast_interface,
                    working_interface,
                )

            multicast = AsyncMotionMulticast(interface=working_interface)
            menuai.data[DOMAIN][KEY_MULTICAST_LISTENER] = multicast
            # start listening for local pushes (only once)
            await multicast.Start_listen()

            # register stop callback to shutdown listening for local pushes
            def stop_motion_multicast(event):
                """Stop multicast thread."""
                _LOGGER.debug("Shutting down Motion Listener")
                multicast.Stop_listen()

            unsub = menuai.bus.async_listen_once(
                EVENT_menuai_STOP, stop_motion_multicast
            )
            menuai.data[DOMAIN][KEY_UNSUB_STOP] = unsub

    # Connect to motion gateway
    multicast = menuai.data[DOMAIN][KEY_MULTICAST_LISTENER]
    connect_gateway_class = ConnectMotionGateway(menuai, multicast)
    if not await connect_gateway_class.async_connect_gateway(
        host, key, blind_type_list
    ):
        raise ConfigEntryNotReady
    motion_gateway = connect_gateway_class.gateway_device
    api_lock = asyncio.Lock()
    coordinator_info = {
        KEY_GATEWAY: motion_gateway,
        KEY_API_LOCK: api_lock,
        CONF_WAIT_FOR_PUSH: wait_for_push,
    }

    coordinator = DataUpdateCoordinatorMotionBlinds(
        menuai, entry, _LOGGER, coordinator_info
    )

    # store blind type list for next time
    if entry.data.get(CONF_BLIND_TYPE_LIST) != motion_gateway.blind_type_list:
        data = {
            **entry.data,
            CONF_BLIND_TYPE_LIST: motion_gateway.blind_type_list,
        }
        menuai.config_entries.async_update_entry(entry, data=data)

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    menuai.data[DOMAIN][entry.entry_id] = {
        KEY_GATEWAY: motion_gateway,
        KEY_COORDINATOR: coordinator,
    }

    if TYPE_CHECKING:
        assert entry.unique_id is not None

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        multicast = menuai.data[DOMAIN][KEY_MULTICAST_LISTENER]
        multicast.Unregister_motion_gateway(config_entry.data[CONF_HOST])
        menuai.data[DOMAIN].pop(config_entry.entry_id)

    if not menuai.config_entries.async_loaded_entries(DOMAIN):
        # No motion gateways left, stop Motion multicast
        unsub_stop = menuai.data[DOMAIN].pop(KEY_UNSUB_STOP)
        unsub_stop()
        _LOGGER.debug("Shutting down Motion Listener")
        multicast = menuai.data[DOMAIN].pop(KEY_MULTICAST_LISTENER)
        multicast.Stop_listen()

    return unload_ok


async def update_listener(menuai: menuai, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(config_entry.entry_id)
