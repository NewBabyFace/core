"""Binary sensor platform for menuai.io addons."""

from __future__ import annotations

from dataclasses import dataclass

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ADDONS_COORDINATOR, ATTR_STARTED, ATTR_STATE, DATA_KEY_ADDONS
from .entity import menuaiioAddonEntity


@dataclass(frozen=True)
class menuaiioBinarySensorEntityDescription(BinarySensorEntityDescription):
    """menuaiio binary sensor entity description."""

    target: str | None = None


ADDON_ENTITY_DESCRIPTIONS = (
    menuaiioBinarySensorEntityDescription(
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_registry_enabled_default=False,
        key=ATTR_STATE,
        translation_key="state",
        target=ATTR_STARTED,
    ),
)


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Binary sensor set up for menuai.io config entry."""
    coordinator = menuai.data[ADDONS_COORDINATOR]

    async_add_entities(
        menuaiioAddonBinarySensor(
            addon=addon,
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for addon in coordinator.data[DATA_KEY_ADDONS].values()
        for entity_description in ADDON_ENTITY_DESCRIPTIONS
    )


class menuaiioAddonBinarySensor(menuaiioAddonEntity, BinarySensorEntity):
    """Binary sensor for menuai.io add-ons."""

    entity_description: menuaiioBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        value = self.coordinator.data[DATA_KEY_ADDONS][self._addon_slug][
            self.entity_description.key
        ]
        if self.entity_description.target is None:
            return value
        return value == self.entity_description.target
