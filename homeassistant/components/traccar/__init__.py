"""Support for Traccar Client."""

from http import HTTPStatus

from aiohttp import web
import voluptuous as vol

from menuai.components import webhook
from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_ID, CONF_WEBHOOK_ID, Platform
from menuai.core import menuai
from menuai.helpers import config_entry_flow, config_validation as cv
from menuai.helpers.dispatcher import async_dispatcher_send

from .const import (
    ATTR_ACCURACY,
    ATTR_ALTITUDE,
    ATTR_BATTERY,
    ATTR_BEARING,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_SPEED,
    ATTR_TIMESTAMP,
    DOMAIN,
)

PLATFORMS = [Platform.DEVICE_TRACKER]


TRACKER_UPDATE = f"{DOMAIN}_tracker_update"


DEFAULT_ACCURACY = 200
DEFAULT_BATTERY = -1


def _id(value: str) -> str:
    """Coerce id by removing '-'."""
    return value.replace("-", "")


WEBHOOK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ID): vol.All(cv.string, _id),
        vol.Required(ATTR_LATITUDE): cv.latitude,
        vol.Required(ATTR_LONGITUDE): cv.longitude,
        vol.Optional(ATTR_ACCURACY, default=DEFAULT_ACCURACY): vol.Coerce(float),
        vol.Optional(ATTR_ALTITUDE): vol.Coerce(float),
        vol.Optional(ATTR_BATTERY, default=DEFAULT_BATTERY): vol.Coerce(float),
        vol.Optional(ATTR_BEARING): vol.Coerce(float),
        vol.Optional(ATTR_SPEED): vol.Coerce(float),
        vol.Optional(ATTR_TIMESTAMP): vol.Coerce(int),
    },
    extra=vol.REMOVE_EXTRA,
)


async def handle_webhook(
    menuai: menuai, webhook_id: str, request: web.Request
) -> web.Response:
    """Handle incoming webhook with Traccar Client request."""
    try:
        data = WEBHOOK_SCHEMA(dict(request.query))
    except vol.MultipleInvalid as error:
        return web.Response(
            text=error.error_message, status=HTTPStatus.UNPROCESSABLE_ENTITY
        )

    attrs = {
        ATTR_ALTITUDE: data.get(ATTR_ALTITUDE),
        ATTR_BEARING: data.get(ATTR_BEARING),
        ATTR_SPEED: data.get(ATTR_SPEED),
    }

    device = data[ATTR_ID]

    async_dispatcher_send(
        menuai,
        TRACKER_UPDATE,
        device,
        data[ATTR_LATITUDE],
        data[ATTR_LONGITUDE],
        data[ATTR_BATTERY],
        data[ATTR_ACCURACY],
        attrs,
    )

    return web.Response(text=f"Setting location for {device}")


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Configure based on config entry."""
    menuai.data.setdefault(DOMAIN, {"devices": set(), "unsub_device_tracker": {}})
    webhook.async_register(
        menuai, DOMAIN, "Traccar", entry.data[CONF_WEBHOOK_ID], handle_webhook
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook.async_unregister(menuai, entry.data[CONF_WEBHOOK_ID])
    menuai.data[DOMAIN]["unsub_device_tracker"].pop(entry.entry_id)()
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async_remove_entry = config_entry_flow.webhook_async_remove_entry
