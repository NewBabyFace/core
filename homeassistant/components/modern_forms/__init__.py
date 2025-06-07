"""The Modern Forms integration."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
import logging
from typing import Any, Concatenate

from aiomodernforms import ModernFormsConnectionError, ModernFormsError

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import ModernFormsDataUpdateCoordinator
from .entity import ModernFormsDeviceEntity

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.FAN,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a Modern Forms device from a config entry."""

    # Create Modern Forms instance for this entry
    coordinator = ModernFormsDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = coordinator

    # Set up all platforms for this device/entry.
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload Modern Forms config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        del menuai.data[DOMAIN][entry.entry_id]

    if not menuai.data[DOMAIN]:
        del menuai.data[DOMAIN]

    return unload_ok


def modernforms_exception_handler[
    _ModernFormsDeviceEntityT: ModernFormsDeviceEntity,
    **_P,
](
    func: Callable[Concatenate[_ModernFormsDeviceEntityT, _P], Any],
) -> Callable[Concatenate[_ModernFormsDeviceEntityT, _P], Coroutine[Any, Any, None]]:
    """Decorate Modern Forms calls to handle Modern Forms exceptions.

    A decorator that wraps the passed in function, catches Modern Forms errors,
    and handles the availability of the device in the data coordinator.
    """

    async def handler(
        self: _ModernFormsDeviceEntityT, *args: _P.args, **kwargs: _P.kwargs
    ) -> None:
        try:
            await func(self, *args, **kwargs)
            self.coordinator.async_update_listeners()

        except ModernFormsConnectionError as error:
            _LOGGER.error("Error communicating with API: %s", error)
            self.coordinator.last_update_success = False
            self.coordinator.async_update_listeners()

        except ModernFormsError as error:
            _LOGGER.error("Invalid response from API: %s", error)

    return handler
