"""Base entity for Streamlabs integration."""

from menuai.core import DOMAIN as menuai_DOMAIN
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.update_coordinator import CoordinatorEntity

from .coordinator import StreamlabsCoordinator, StreamlabsData


class StreamlabsWaterEntity(CoordinatorEntity[StreamlabsCoordinator]):
    """Defines a base Streamlabs entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: StreamlabsCoordinator,
        location_id: str,
        key: str,
    ) -> None:
        """Initialize the Streamlabs entity."""
        super().__init__(coordinator)
        self._location_id = location_id
        self._attr_unique_id = f"{location_id}-{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(menuai_DOMAIN, location_id)},
            name=self.location_data.name,
        )

    @property
    def location_data(self) -> StreamlabsData:
        """Returns the data object."""
        return self.coordinator.data[self._location_id]
