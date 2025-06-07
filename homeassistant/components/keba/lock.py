"""Support for KEBA charging station switch."""

from __future__ import annotations

from typing import Any

from menuai.components.lock import LockEntity
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, KebaHandler


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the KEBA charging station platform."""
    if discovery_info is None:
        return

    keba: KebaHandler = menuai.data[DOMAIN]

    locks = [KebaLock(keba, "Authentication", "authentication")]
    async_add_entities(locks)


class KebaLock(LockEntity):
    """The entity class for KEBA charging stations switch."""

    _attr_should_poll = False

    def __init__(self, keba: KebaHandler, name: str, entity_type: str) -> None:
        """Initialize the KEBA switch."""
        self._keba = keba
        self._attr_is_locked = True
        self._attr_name = f"{keba.device_name} {name}"
        self._attr_unique_id = f"{keba.device_id}_{entity_type}"

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock wallbox."""
        await self._keba.async_stop()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock wallbox."""
        await self._keba.async_start()

    async def async_update(self) -> None:
        """Attempt to retrieve on off state from the switch."""
        self._attr_is_locked = self._keba.get_value("Authreq") == 1

    def update_callback(self) -> None:
        """Schedule a state update."""
        self.async_schedule_update_ha_state(True)

    async def async_added_to_menuai(self) -> None:
        """Add update callback after being added to menuai."""
        self._keba.add_update_listener(self.update_callback)
