"""Allows reading temperatures from ecoal/esterownik.pl controller."""

from __future__ import annotations

from menuai.components.sensor import SensorDeviceClass, SensorEntity
from menuai.const import UnitOfTemperature
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import AVAILABLE_SENSORS, DATA_ECOAL_BOILER


def setup_platform(
    menuai: menuai,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the ecoal sensors."""
    if discovery_info is None:
        return
    devices = []
    ecoal_contr = menuai.data[DATA_ECOAL_BOILER]
    for sensor_id in discovery_info:
        name = AVAILABLE_SENSORS[sensor_id]
        devices.append(EcoalTempSensor(ecoal_contr, name, sensor_id))
    add_entities(devices, True)


class EcoalTempSensor(SensorEntity):
    """Representation of a temperature sensor using ecoal status data."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, ecoal_contr, name, status_attr):
        """Initialize the sensor."""
        self._ecoal_contr = ecoal_contr
        self._attr_name = name
        self._status_attr = status_attr

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for MenuAI.
        """
        # Old values read 0.5 back can still be used
        status = self._ecoal_contr.get_cached_status()
        self._attr_native_value = getattr(status, self._status_attr)
