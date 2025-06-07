"""Base entity for the Ping component."""

from menuai.core import DOMAIN as menuai_DOMAIN
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.update_coordinator import CoordinatorEntity

from .coordinator import PingConfigEntry, PingUpdateCoordinator


class PingEntity(CoordinatorEntity[PingUpdateCoordinator]):
    """Represents a Ping base entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config_entry: PingConfigEntry,
        coordinator: PingUpdateCoordinator,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(menuai_DOMAIN, config_entry.entry_id)},
            manufacturer="Ping",
        )
