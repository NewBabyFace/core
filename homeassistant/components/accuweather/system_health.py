"""Provide info to system health."""

from __future__ import annotations

from typing import Any

from accuweather.const import ENDPOINT

from menuai.components import system_health
from menuai.core import menuai, callback

from .const import DOMAIN
from .coordinator import AccuWeatherConfigEntry


@callback
def async_register(
    menuai: menuai, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)


async def system_health_info(menuai: menuai) -> dict[str, Any]:
    """Get info for the info page."""
    config_entry: AccuWeatherConfigEntry = menuai.config_entries.async_entries(DOMAIN)[0]

    remaining_requests = (
        config_entry.runtime_data.coordinator_observation.accuweather.requests_remaining
    )

    return {
        "can_reach_server": system_health.async_check_can_reach_url(menuai, ENDPOINT),
        "remaining_requests": remaining_requests,
    }
