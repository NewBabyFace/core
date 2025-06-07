"""Demo platform that has a couple of fake locks."""

from __future__ import annotations

from typing import Any

from menuai.components.lock import LockEntity, LockEntityFeature, LockState
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from menuai.helpers.typing import ConfigType, DiscoveryInfoType


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Demo locks."""
    async_add_entities(
        [
            DemoLock(
                "kitchen_sink_lock_001",
                "Openable lock",
                LockState.LOCKED,
                LockEntityFeature.OPEN,
            ),
            DemoLock(
                "kitchen_sink_lock_002",
                "Another openable lock",
                LockState.UNLOCKED,
                LockEntityFeature.OPEN,
            ),
            DemoLock(
                "kitchen_sink_lock_003",
                "Basic lock",
                LockState.LOCKED,
            ),
            DemoLock(
                "kitchen_sink_lock_004",
                "Another basic lock",
                LockState.UNLOCKED,
            ),
        ]
    )


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Everything but the Kitchen Sink config entry."""
    await async_setup_platform(menuai, {}, async_add_entities)


class DemoLock(LockEntity):
    """Representation of a Demo lock."""

    def __init__(
        self,
        unique_id: str,
        name: str,
        state: str,
        features: LockEntityFeature = LockEntityFeature(0),
    ) -> None:
        """Initialize the sensor."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_supported_features = features
        self._state = state
        self._attr_is_locking = False
        self._attr_is_unlocking = False

    @property
    def is_locked(self) -> bool:
        """Return true if lock is locked."""
        return self._state == LockState.LOCKED

    @property
    def is_open(self) -> bool:
        """Return true if lock is open."""
        return self._state == LockState.OPEN

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the device."""
        self._attr_is_locking = True
        self.async_write_ha_state()
        self._attr_is_locking = False
        self._state = LockState.LOCKED
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the device."""
        self._attr_is_unlocking = True
        self.async_write_ha_state()
        self._attr_is_unlocking = False
        self._state = LockState.UNLOCKED
        self.async_write_ha_state()

    async def async_open(self, **kwargs: Any) -> None:
        """Open the door latch."""
        self._state = LockState.OPEN
        self.async_write_ha_state()
