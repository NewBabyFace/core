"""Button entity to set the time of the Alpha2 base."""

from menuai.components.button import ButtonEntity
from menuai.config_entries import ConfigEntry
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.update_coordinator import CoordinatorEntity
from menuai.util import dt as dt_util

from .const import DOMAIN
from .coordinator import Alpha2BaseCoordinator


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add Alpha2 button entities."""

    coordinator: Alpha2BaseCoordinator = menuai.data[DOMAIN][config_entry.entry_id]

    async_add_entities([Alpha2TimeSyncButton(coordinator, config_entry.entry_id)])


class Alpha2TimeSyncButton(CoordinatorEntity[Alpha2BaseCoordinator], ButtonEntity):
    """Alpha2 virtual time sync button."""

    _attr_name = "Sync time"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: Alpha2BaseCoordinator, entry_id: str) -> None:
        """Initialize Alpha2TimeSyncButton."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{entry_id}:sync_time"

    async def async_press(self) -> None:
        """Synchronize current local time from HA instance to base station."""
        await self.coordinator.base.set_datetime(dt_util.now())
