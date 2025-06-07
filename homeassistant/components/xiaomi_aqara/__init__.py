"""Support for Xiaomi Gateways."""

import asyncio
import logging

import voluptuous as vol
from xiaomi_gateway import AsyncXiaomiGatewayMulticast, XiaomiGateway

from menuai.components import persistent_notification
from menuai.config_entries import ConfigEntry
from menuai.const import (
    ATTR_DEVICE_ID,
    CONF_HOST,
    CONF_PORT,
    CONF_PROTOCOL,
    EVENT_menuai_STOP,
    Platform,
)
from menuai.core import menuai, ServiceCall, callback
from menuai.helpers import config_validation as cv, device_registry as dr
from menuai.helpers.typing import ConfigType

from .const import (
    CONF_INTERFACE,
    CONF_KEY,
    CONF_SID,
    DEFAULT_DISCOVERY_RETRY,
    DOMAIN,
    GATEWAYS_KEY,
    KEY_SETUP_LOCK,
    KEY_UNSUB_STOP,
    LISTENER_KEY,
)

_LOGGER = logging.getLogger(__name__)

GATEWAY_PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.COVER,
    Platform.LIGHT,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
]
GATEWAY_PLATFORMS_NO_KEY = [Platform.BINARY_SENSOR, Platform.SENSOR]

ATTR_GW_MAC = "gw_mac"
ATTR_RINGTONE_ID = "ringtone_id"
ATTR_RINGTONE_VOL = "ringtone_vol"

SERVICE_PLAY_RINGTONE = "play_ringtone"
SERVICE_STOP_RINGTONE = "stop_ringtone"
SERVICE_ADD_DEVICE = "add_device"
SERVICE_REMOVE_DEVICE = "remove_device"

SERVICE_SCHEMA_PLAY_RINGTONE = vol.Schema(
    {
        vol.Required(ATTR_RINGTONE_ID): vol.All(
            vol.Coerce(int), vol.NotIn([9, 14, 15, 16, 17, 18, 19])
        ),
        vol.Optional(ATTR_RINGTONE_VOL): vol.All(
            vol.Coerce(int), vol.Clamp(min=0, max=100)
        ),
    }
)

SERVICE_SCHEMA_REMOVE_DEVICE = vol.Schema(
    {vol.Required(ATTR_DEVICE_ID): vol.All(cv.string, vol.Length(min=14, max=14))}
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Xiaomi component."""

    def play_ringtone_service(call: ServiceCall) -> None:
        """Service to play ringtone through Gateway."""
        ring_id = call.data.get(ATTR_RINGTONE_ID)
        gateway: XiaomiGateway = call.data[ATTR_GW_MAC]

        kwargs = {"mid": ring_id}

        if (ring_vol := call.data.get(ATTR_RINGTONE_VOL)) is not None:
            kwargs["vol"] = ring_vol

        gateway.write_to_hub(gateway.sid, **kwargs)

    def stop_ringtone_service(call: ServiceCall) -> None:
        """Service to stop playing ringtone on Gateway."""
        gateway: XiaomiGateway = call.data[ATTR_GW_MAC]
        gateway.write_to_hub(gateway.sid, mid=10000)

    def add_device_service(call: ServiceCall) -> None:
        """Service to add a new sub-device within the next 30 seconds."""
        gateway: XiaomiGateway = call.data[ATTR_GW_MAC]
        gateway.write_to_hub(gateway.sid, join_permission="yes")
        persistent_notification.async_create(
            menuai,
            (
                "Join permission enabled for 30 seconds! "
                "Please press the pairing button of the new device once."
            ),
            title="Xiaomi Aqara Gateway",
        )

    def remove_device_service(call: ServiceCall) -> None:
        """Service to remove a sub-device from the gateway."""
        device_id = call.data.get(ATTR_DEVICE_ID)
        gateway: XiaomiGateway = call.data[ATTR_GW_MAC]
        gateway.write_to_hub(gateway.sid, remove_device=device_id)

    gateway_only_schema = _add_gateway_to_schema(menuai, vol.Schema({}))

    menuai.services.register(
        DOMAIN,
        SERVICE_PLAY_RINGTONE,
        play_ringtone_service,
        schema=_add_gateway_to_schema(menuai, SERVICE_SCHEMA_PLAY_RINGTONE),
    )

    menuai.services.register(
        DOMAIN, SERVICE_STOP_RINGTONE, stop_ringtone_service, schema=gateway_only_schema
    )

    menuai.services.register(
        DOMAIN, SERVICE_ADD_DEVICE, add_device_service, schema=gateway_only_schema
    )

    menuai.services.register(
        DOMAIN,
        SERVICE_REMOVE_DEVICE,
        remove_device_service,
        schema=_add_gateway_to_schema(menuai, SERVICE_SCHEMA_REMOVE_DEVICE),
    )

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up the xiaomi aqara components from a config entry."""
    menuai.data.setdefault(DOMAIN, {})
    setup_lock = menuai.data[DOMAIN].setdefault(KEY_SETUP_LOCK, asyncio.Lock())
    menuai.data[DOMAIN].setdefault(GATEWAYS_KEY, {})

    # Connect to Xiaomi Aqara Gateway
    xiaomi_gateway = await menuai.async_add_executor_job(
        XiaomiGateway,
        entry.data[CONF_HOST],
        entry.data[CONF_SID],
        entry.data[CONF_KEY],
        DEFAULT_DISCOVERY_RETRY,
        entry.data[CONF_INTERFACE],
        entry.data[CONF_PORT],
        entry.data[CONF_PROTOCOL],
    )
    menuai.data[DOMAIN][GATEWAYS_KEY][entry.entry_id] = xiaomi_gateway

    async with setup_lock:
        if LISTENER_KEY not in menuai.data[DOMAIN]:
            multicast = AsyncXiaomiGatewayMulticast(
                interface=entry.data[CONF_INTERFACE]
            )
            menuai.data[DOMAIN][LISTENER_KEY] = multicast

            # start listining for local pushes (only once)
            await multicast.start_listen()

            # register stop callback to shutdown listining for local pushes
            @callback
            def stop_xiaomi(event):
                """Stop Xiaomi Socket."""
                _LOGGER.debug("Shutting down Xiaomi Gateway Listener")
                multicast.stop_listen()

            unsub = menuai.bus.async_listen_once(EVENT_menuai_STOP, stop_xiaomi)
            menuai.data[DOMAIN][KEY_UNSUB_STOP] = unsub

    multicast = menuai.data[DOMAIN][LISTENER_KEY]
    multicast.register_gateway(entry.data[CONF_HOST], xiaomi_gateway.multicast_callback)
    _LOGGER.debug(
        "Gateway with host '%s' connected, listening for broadcasts",
        entry.data[CONF_HOST],
    )

    assert entry.unique_id
    device_registry = dr.async_get(menuai)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id)},
        manufacturer="Xiaomi Aqara",
        name=entry.title,
        sw_version=entry.data[CONF_PROTOCOL],
    )

    if entry.data[CONF_KEY] is not None:
        platforms = GATEWAY_PLATFORMS
    else:
        platforms = GATEWAY_PLATFORMS_NO_KEY

    await menuai.config_entries.async_forward_entry_setups(entry, platforms)

    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if config_entry.data[CONF_KEY] is not None:
        platforms = GATEWAY_PLATFORMS
    else:
        platforms = GATEWAY_PLATFORMS_NO_KEY

    unload_ok = await menuai.config_entries.async_unload_platforms(
        config_entry, platforms
    )
    if unload_ok:
        menuai.data[DOMAIN][GATEWAYS_KEY].pop(config_entry.entry_id)

    if not menuai.config_entries.async_loaded_entries(DOMAIN):
        # No gateways left, stop Xiaomi socket
        unsub_stop = menuai.data[DOMAIN].pop(KEY_UNSUB_STOP)
        unsub_stop()
        menuai.data[DOMAIN].pop(GATEWAYS_KEY)
        _LOGGER.debug("Shutting down Xiaomi Gateway Listener")
        multicast = menuai.data[DOMAIN].pop(LISTENER_KEY)
        multicast.stop_listen()

    return unload_ok


def _add_gateway_to_schema(menuai, schema):
    """Extend a voluptuous schema with a gateway validator."""

    def gateway(sid):
        """Convert sid to a gateway."""
        sid = str(sid).replace(":", "").lower()

        for gateway in menuai.data[DOMAIN][GATEWAYS_KEY].values():
            if gateway.sid == sid:
                return gateway

        raise vol.Invalid(f"Unknown gateway sid {sid}")

    kwargs = {}
    if (xiaomi_data := menuai.data.get(DOMAIN)) is not None:
        gateways = list(xiaomi_data[GATEWAYS_KEY].values())

        # If the user has only 1 gateway, make it the default for services.
        if len(gateways) == 1:
            kwargs["default"] = gateways[0].sid

    return schema.extend({vol.Required(ATTR_GW_MAC, **kwargs): gateway})
