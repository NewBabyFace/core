"""Provide info to system health."""

from menuai.components import system_health
from menuai.core import menuai, callback

IPMA_API_URL = "http://api.ipma.pt"


@callback
def async_register(
    menuai: menuai, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)


async def system_health_info(menuai):
    """Get info for the info page."""
    return {
        "api_endpoint_reachable": system_health.async_check_can_reach_url(
            menuai, IPMA_API_URL
        )
    }
