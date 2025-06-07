"""Advantage Air Update platform."""

from menuai.components.update import UpdateEntity
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AdvantageAirDataConfigEntry
from .const import DOMAIN
from .entity import AdvantageAirEntity
from .models import AdvantageAirData


async def async_setup_entry(
    menuai: menuai,
    config_entry: AdvantageAirDataConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up AdvantageAir update platform."""

    instance = config_entry.runtime_data

    async_add_entities([AdvantageAirApp(instance)])


class AdvantageAirApp(AdvantageAirEntity, UpdateEntity):
    """Representation of Advantage Air App."""

    _attr_name = "App"

    def __init__(self, instance: AdvantageAirData) -> None:
        """Initialize the Advantage Air App."""
        super().__init__(instance)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.data["system"]["rid"])},
            manufacturer="Advantage Air",
            model=self.coordinator.data["system"]["sysType"],
            name=self.coordinator.data["system"]["name"],
            sw_version=self.coordinator.data["system"]["myAppRev"],
        )

    @property
    def installed_version(self) -> str:
        """Return the current app version."""
        return self.coordinator.data["system"]["myAppRev"]

    @property
    def latest_version(self) -> str:
        """Return if there is an update."""
        if self.coordinator.data["system"]["needsUpdate"]:
            return "Needs Update"
        return self.installed_version
