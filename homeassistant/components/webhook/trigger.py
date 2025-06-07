"""Offer webhook triggered automation rules."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from aiohttp import hdrs, web
import voluptuous as vol

from menuai.const import CONF_PLATFORM, CONF_WEBHOOK_ID
from menuai.core import CALLBACK_TYPE, menuaiJob, menuai, callback
from menuai.helpers import config_validation as cv
from menuai.helpers.trigger import TriggerActionType, TriggerInfo
from menuai.helpers.typing import ConfigType

from . import (
    DEFAULT_METHODS,
    DOMAIN,
    SUPPORTED_METHODS,
    async_register,
    async_unregister,
)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ("webhook",)

CONF_ALLOWED_METHODS = "allowed_methods"
CONF_LOCAL_ONLY = "local_only"

TRIGGER_SCHEMA = cv.TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_PLATFORM): "webhook",
        vol.Required(CONF_WEBHOOK_ID): cv.string,
        vol.Optional(CONF_ALLOWED_METHODS): vol.All(
            cv.ensure_list,
            [vol.All(vol.Upper, vol.In(SUPPORTED_METHODS))],
            vol.Unique(),
        ),
        vol.Optional(CONF_LOCAL_ONLY): bool,
    }
)

WEBHOOK_TRIGGERS = f"{DOMAIN}_triggers"


@dataclass(slots=True)
class TriggerInstance:
    """Attached trigger settings."""

    trigger_info: TriggerInfo
    job: menuaiJob


async def _handle_webhook(
    menuai: menuai, webhook_id: str, request: web.Request
) -> None:
    """Handle incoming webhook."""
    base_result: dict[str, Any] = {"platform": "webhook", "webhook_id": webhook_id}

    if "json" in request.headers.get(hdrs.CONTENT_TYPE, ""):
        base_result["json"] = await request.json()
    else:
        base_result["data"] = await request.post()

    base_result["query"] = request.query
    base_result["description"] = "webhook"

    triggers: dict[str, list[TriggerInstance]] = menuai.data.setdefault(
        WEBHOOK_TRIGGERS, {}
    )
    for trigger in triggers[webhook_id]:
        result = {**base_result, **trigger.trigger_info["trigger_data"]}
        menuai.async_run_menuai_job(trigger.job, {"trigger": result})


async def async_attach_trigger(
    menuai: menuai,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Trigger based on incoming webhooks."""
    webhook_id: str = config[CONF_WEBHOOK_ID]
    local_only = config.get(CONF_LOCAL_ONLY, True)
    allowed_methods = config.get(CONF_ALLOWED_METHODS, DEFAULT_METHODS)
    job = menuaiJob(action)

    triggers: dict[str, list[TriggerInstance]] = menuai.data.setdefault(
        WEBHOOK_TRIGGERS, {}
    )

    if webhook_id not in triggers:
        async_register(
            menuai,
            trigger_info["domain"],
            trigger_info["name"],
            webhook_id,
            _handle_webhook,
            local_only=local_only,
            allowed_methods=allowed_methods,
        )
        triggers[webhook_id] = []

    trigger_instance = TriggerInstance(trigger_info, job)
    triggers[webhook_id].append(trigger_instance)

    @callback
    def unregister() -> None:
        """Unregister webhook."""
        triggers[webhook_id].remove(trigger_instance)
        if not triggers[webhook_id]:
            async_unregister(menuai, webhook_id)
            triggers.pop(webhook_id)

    return unregister
