"""Support the ElkM1 Gold and ElkM1 EZ8 alarm/integration panels."""

from __future__ import annotations

from elkm1_lib.elk import Elk, Panel
import voluptuous as vol

from menuai.core import menuai, ServiceCall, callback
from menuai.exceptions import menuaiError
from menuai.helpers import config_validation as cv
from menuai.util import dt as dt_util

from .const import DOMAIN
from .models import ELKM1Data

SPEAK_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("number"): vol.All(vol.Coerce(int), vol.Range(min=0, max=999)),
        vol.Optional("prefix", default=""): cv.string,
    }
)

SET_TIME_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("prefix", default=""): cv.string,
    }
)


def _find_elk_by_prefix(menuai: menuai, prefix: str) -> Elk | None:
    """Search all config entries for a given prefix."""
    for entry in menuai.config_entries.async_entries(DOMAIN):
        if not entry.runtime_data:
            continue
        elk_data: ELKM1Data = entry.runtime_data
        if elk_data.prefix == prefix:
            return elk_data.elk
    return None


@callback
def _async_get_elk_panel(service: ServiceCall) -> Panel:
    """Get the ElkM1 panel from a service call."""
    prefix = service.data["prefix"]
    elk = _find_elk_by_prefix(service.menuai, prefix)
    if elk is None:
        raise menuaiError(f"No ElkM1 with prefix '{prefix}' found")
    return elk.panel


@callback
def _speak_word_service(service: ServiceCall) -> None:
    _async_get_elk_panel(service).speak_word(service.data["number"])


@callback
def _speak_phrase_service(service: ServiceCall) -> None:
    _async_get_elk_panel(service).speak_phrase(service.data["number"])


@callback
def _set_time_service(service: ServiceCall) -> None:
    _async_get_elk_panel(service).set_time(dt_util.now())


def async_setup_services(menuai: menuai) -> None:
    """Create ElkM1 services."""

    menuai.services.async_register(
        DOMAIN, "speak_word", _speak_word_service, SPEAK_SERVICE_SCHEMA
    )
    menuai.services.async_register(
        DOMAIN, "speak_phrase", _speak_phrase_service, SPEAK_SERVICE_SCHEMA
    )
    menuai.services.async_register(
        DOMAIN, "set_time", _set_time_service, SET_TIME_SERVICE_SCHEMA
    )
