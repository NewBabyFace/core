"""Support for the Abode Security System locks."""

from typing import Any

from jaraco.abode.devices.lock import Lock

from menuai.components.lock import LockEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AbodeSystem
from .const import DOMAIN
from .entity import AbodeDevice


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode lock devices."""
    data: AbodeSystem = menuai.data[DOMAIN]

    async_add_entities(
        AbodeLock(data, device)
        for device in data.abode.get_devices(generic_type="lock")
    )


class AbodeLock(AbodeDevice, LockEntity):
    """Representation of an Abode lock."""

    _device: Lock
    _attr_name = None

    def lock(self, **kwargs: Any) -> None:
        """Lock the device."""
        self._device.lock()

    def unlock(self, **kwargs: Any) -> None:
        """Unlock the device."""
        self._device.unlock()

    @property
    def is_locked(self) -> bool:
        """Return true if device is on."""
        return bool(self._device.is_locked)
