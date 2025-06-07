"""Provide info to system health."""

from typing import Any

from menuai.components import system_health
from menuai.core import menuai, callback


@callback
def async_register(
    menuai: menuai, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)


async def system_health_info(menuai: menuai) -> dict[str, Any]:
    """Get info for the info page."""
    return {
        "api_endpoint_reachable": system_health.async_check_can_reach_url(
            menuai, "https://api.spotify.com"
        )
    }
