"""Binary sensor for Wyoming."""

from __future__ import annotations

from typing import TYPE_CHECKING

from menuai.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import WyomingSatelliteEntity

if TYPE_CHECKING:
    from .models import DomainDataItem


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    item: DomainDataItem = menuai.data[DOMAIN][config_entry.entry_id]

    # Setup is only forwarded for satellites
    assert item.device is not None

    async_add_entities([WyomingSatelliteAssistInProgress(item.device)])


class WyomingSatelliteAssistInProgress(WyomingSatelliteEntity, BinarySensorEntity):
    """Entity to represent Assist is in progress for satellite."""

    entity_description = BinarySensorEntityDescription(
        entity_registry_enabled_default=False,
        key="assist_in_progress",
        translation_key="assist_in_progress",
    )
    _attr_is_on = False

    async def async_added_to_menuai(self) -> None:
        """Call when entity about to be added to menuai."""
        await super().async_added_to_menuai()

        self._device.set_is_active_listener(self._is_active_changed)

    @callback
    def _is_active_changed(self) -> None:
        """Call when active state changed."""
        self._attr_is_on = self._device.is_active
        self.async_write_ha_state()
