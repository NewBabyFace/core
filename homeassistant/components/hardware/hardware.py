"""The Hardware integration."""

from __future__ import annotations

from menuai.core import menuai, callback
from menuai.exceptions import menuaiError
from menuai.helpers.integration_platform import (
    async_process_integration_platforms,
)

from .const import DATA_HARDWARE, DOMAIN
from .models import HardwareProtocol


async def async_process_hardware_platforms(
    menuai: menuai,
) -> None:
    """Start processing hardware platforms."""
    await async_process_integration_platforms(
        menuai, DOMAIN, _register_hardware_platform, wait_for_platforms=True
    )


@callback
def _register_hardware_platform(
    menuai: menuai, integration_domain: str, platform: HardwareProtocol
) -> None:
    """Register a hardware platform."""
    if integration_domain == DOMAIN:
        return
    if not hasattr(platform, "async_info"):
        raise menuaiError(f"Invalid hardware platform {platform}")
    menuai.data[DATA_HARDWARE].hardware_platform[integration_domain] = platform
