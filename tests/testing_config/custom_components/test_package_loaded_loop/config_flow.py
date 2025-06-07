"""Config flow."""

from menuai.core import menuai


async def _async_has_devices(menuai: menuai) -> bool:
    return True
