"""Support for Mailgun."""

import hashlib
import hmac
import json
import logging

from aiohttp import web
import voluptuous as vol

from menuai.components import webhook
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, CONF_DOMAIN, CONF_WEBHOOK_ID
from menuai.core import menuai
from menuai.helpers import config_entry_flow, config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_SANDBOX = "sandbox"

DEFAULT_SANDBOX = False

MESSAGE_RECEIVED = f"{DOMAIN}_message_received"

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {
                vol.Required(CONF_API_KEY): cv.string,
                vol.Required(CONF_DOMAIN): cv.string,
                vol.Optional(CONF_SANDBOX, default=DEFAULT_SANDBOX): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Mailgun component."""
    if DOMAIN not in config:
        return True

    menuai.data[DOMAIN] = config[DOMAIN]
    return True


async def handle_webhook(
    menuai: menuai, webhook_id: str, request: web.Request
) -> None:
    """Handle incoming webhook with Mailgun inbound messages."""
    body = await request.text()
    try:
        data = json.loads(body) if body else {}
    except ValueError:
        return

    if (
        isinstance(data, dict)
        and "signature" in data
        and await verify_webhook(menuai, **data["signature"])
    ):
        data["webhook_id"] = webhook_id
        menuai.bus.async_fire(MESSAGE_RECEIVED, data)
        return

    _LOGGER.warning(
        "Mailgun webhook received an unauthenticated message - webhook_id: %s",
        webhook_id,
    )


async def verify_webhook(menuai, token=None, timestamp=None, signature=None):
    """Verify webhook was signed by Mailgun."""
    if DOMAIN not in menuai.data:
        _LOGGER.warning("Cannot validate Mailgun webhook, missing API Key")
        return True

    if not (token and timestamp and signature):
        return False

    hmac_digest = hmac.new(
        key=bytes(menuai.data[DOMAIN][CONF_API_KEY], "utf-8"),
        msg=bytes(f"{timestamp}{token}", "utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, hmac_digest)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Configure based on config entry."""
    webhook.async_register(
        menuai, DOMAIN, "Mailgun", entry.data[CONF_WEBHOOK_ID], handle_webhook
    )
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook.async_unregister(menuai, entry.data[CONF_WEBHOOK_ID])
    return True


async_remove_entry = config_entry_flow.webhook_async_remove_entry
