"""Support for Streamlabs Water Monitor Away Mode."""

from __future__ import annotations

from menuai.components.binary_sensor import BinarySensorEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StreamlabsCoordinator
from .const import DOMAIN
from .entity import StreamlabsWaterEntity


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Streamlabs water binary sensor from a config entry."""
    coordinator = menuai.data[DOMAIN][entry.entry_id]

    async_add_entities(
        StreamlabsAwayMode(coordinator, location_id) for location_id in coordinator.data
    )


class StreamlabsAwayMode(StreamlabsWaterEntity, BinarySensorEntity):
    """Monitor the away mode state."""

    _attr_translation_key = "away_mode"

    def __init__(self, coordinator: StreamlabsCoordinator, location_id: str) -> None:
        """Initialize the away mode device."""
        super().__init__(coordinator, location_id, "away_mode")

    @property
    def is_on(self) -> bool:
        """Return if away mode is on."""
        return self.location_data.is_away
