"""Config flow for the NEW_NAME integration."""

import my_pypi_dependency

from menuai.core import menuai
from menuai.helpers import config_entry_flow

from .const import DOMAIN


async def _async_has_devices(menuai: menuai) -> bool:
    """Return if there are devices that can be discovered."""
    # TODO Check if there are any devices that can be discovered in the network.
    devices = await menuai.async_add_executor_job(my_pypi_dependency.discover)
    return len(devices) > 0


config_entry_flow.register_discovery_flow(DOMAIN, "NEW_NAME", _async_has_devices)
