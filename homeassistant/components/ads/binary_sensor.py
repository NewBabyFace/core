"""Support for ADS binary sensors."""

from __future__ import annotations

import pyads
import voluptuous as vol

from menuai.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    PLATFORM_SCHEMA as BINARY_SENSOR_PLATFORM_SCHEMA,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from menuai.const import CONF_DEVICE_CLASS, CONF_NAME
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_ADS_VAR, DATA_ADS, STATE_KEY_STATE
from .entity import AdsEntity
from .hub import AdsHub

DEFAULT_NAME = "ADS binary sensor"
PLATFORM_SCHEMA = BINARY_SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ADS_VAR): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }
)


def setup_platform(
    menuai: menuai,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Binary Sensor platform for ADS."""
    ads_hub = menuai.data[DATA_ADS]

    ads_var: str = config[CONF_ADS_VAR]
    name: str = config[CONF_NAME]
    device_class: BinarySensorDeviceClass | None = config.get(CONF_DEVICE_CLASS)

    ads_sensor = AdsBinarySensor(ads_hub, name, ads_var, device_class)
    add_entities([ads_sensor])


class AdsBinarySensor(AdsEntity, BinarySensorEntity):
    """Representation of ADS binary sensors."""

    def __init__(
        self,
        ads_hub: AdsHub,
        name: str,
        ads_var: str,
        device_class: BinarySensorDeviceClass | None,
    ) -> None:
        """Initialize ADS binary sensor."""
        super().__init__(ads_hub, name, ads_var)
        self._attr_device_class = device_class or BinarySensorDeviceClass.MOVING

    async def async_added_to_menuai(self) -> None:
        """Register device notification."""
        await self.async_initialize_device(self._ads_var, pyads.PLCTYPE_BOOL)

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self._state_dict[STATE_KEY_STATE]
