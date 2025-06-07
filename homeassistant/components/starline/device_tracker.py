"""StarLine device tracker."""

from typing import Any

from menuai.components.device_tracker import TrackerEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.restore_state import RestoreEntity

from .account import StarlineAccount, StarlineDevice
from .const import DOMAIN
from .entity import StarlineEntity


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up StarLine entry."""
    account: StarlineAccount = menuai.data[DOMAIN][entry.entry_id]
    async_add_entities(
        StarlineDeviceTracker(account, device)
        for device in account.api.devices.values()
        if device.support_position
    )


class StarlineDeviceTracker(StarlineEntity, TrackerEntity, RestoreEntity):
    """StarLine device tracker."""

    _attr_translation_key = "location"

    def __init__(self, account: StarlineAccount, device: StarlineDevice) -> None:
        """Set up StarLine entity."""
        super().__init__(account, device, "location")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific attributes."""
        return self._account.gps_attrs(self._device)

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device."""
        return self._device.battery_level

    @property
    def location_accuracy(self) -> float:
        """Return the gps accuracy of the device."""
        return self._device.position.get("r", 0)

    @property
    def latitude(self) -> float:
        """Return latitude value of the device."""
        return self._device.position["x"]

    @property
    def longitude(self) -> float:
        """Return longitude value of the device."""
        return self._device.position["y"]
