"""Config flow."""

from menuai.config_entries import ConfigFlow
from menuai.core import menuai


class MockConfigFlow(
    ConfigFlow, domain="test_package_raises_cancelled_error_config_entry"
):
    """Mock config flow."""


async def _async_has_devices(menuai: menuai) -> bool:
    """Return if there are devices that can be discovered."""
    return True
