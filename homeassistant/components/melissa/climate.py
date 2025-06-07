"""Support for Melissa Climate A/C."""

from __future__ import annotations

import logging
from typing import Any

from menuai.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from menuai.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import DATA_MELISSA

_LOGGER = logging.getLogger(__name__)

OP_MODES = [
    HVACMode.HEAT,
    HVACMode.COOL,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.OFF,
]

FAN_MODES = [FAN_AUTO, FAN_HIGH, FAN_MEDIUM, FAN_LOW]


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Iterate through and add all Melissa devices."""
    api = menuai.data[DATA_MELISSA]
    devices = (await api.async_fetch_devices()).values()

    async_add_entities(
        (
            MelissaClimate(api, device["serial_number"], device)
            for device in devices
            if device["type"] == "melissa"
        ),
        True,
    )


class MelissaClimate(ClimateEntity):
    """Representation of a Melissa Climate device."""

    _attr_fan_modes = FAN_MODES
    _attr_hvac_modes = OP_MODES
    _attr_supported_features = (
        ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_target_temperature_step = PRECISION_WHOLE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 16
    _attr_max_temp = 30

    def __init__(self, api, serial_number, init_data):
        """Initialize the climate device."""
        self._attr_name = init_data["name"]
        self._api = api
        self._serial_number = serial_number
        self._data = init_data["controller_log"]
        self._state = None
        self._cur_settings = None

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan mode."""
        if self._cur_settings is not None:
            return self.melissa_fan_to_menuai(self._cur_settings[self._api.FAN])
        return None

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if self._data:
            return self._data[self._api.TEMP]
        return None

    @property
    def current_humidity(self) -> float | None:
        """Return the current humidity value."""
        if self._data:
            return self._data[self._api.HUMIDITY]
        return None

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current operation mode."""
        if self._cur_settings is None:
            return None

        is_on = self._cur_settings[self._api.STATE] in (
            self._api.STATE_ON,
            self._api.STATE_IDLE,
        )

        if not is_on:
            return HVACMode.OFF

        return self.melissa_op_to_menuai(self._cur_settings[self._api.MODE])

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self._cur_settings is None:
            return None
        return self._cur_settings[self._api.TEMP]

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        await self.async_send({self._api.TEMP: temp})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        melissa_fan_mode = self.menuai_fan_to_melissa(fan_mode)
        await self.async_send({self._api.FAN: melissa_fan_mode})

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set operation mode."""
        if hvac_mode == HVACMode.OFF:
            await self.async_send({self._api.STATE: self._api.STATE_OFF})
            return

        mode = self.menuai_mode_to_melissa(hvac_mode)
        await self.async_send(
            {self._api.MODE: mode, self._api.STATE: self._api.STATE_ON}
        )

    async def async_send(self, value):
        """Send action to service."""
        try:
            old_value = self._cur_settings.copy()
            self._cur_settings.update(value)
        except AttributeError:
            old_value = None
        if not await self._api.async_send(
            self._serial_number, "melissa", self._cur_settings
        ):
            self._cur_settings = old_value

    async def async_update(self) -> None:
        """Get latest data from Melissa."""
        try:
            self._data = (await self._api.async_status(cached=True))[
                self._serial_number
            ]
            self._cur_settings = (
                await self._api.async_cur_settings(self._serial_number)
            )["controller"]["_relation"]["command_log"]
        except KeyError:
            _LOGGER.warning("Unable to update entity %s", self.entity_id)

    def melissa_op_to_menuai(self, mode):
        """Translate Melissa modes to menuai states."""
        if mode == self._api.MODE_HEAT:
            return HVACMode.HEAT
        if mode == self._api.MODE_COOL:
            return HVACMode.COOL
        if mode == self._api.MODE_DRY:
            return HVACMode.DRY
        if mode == self._api.MODE_FAN:
            return HVACMode.FAN_ONLY
        _LOGGER.warning("Operation mode %s could not be mapped to menuai", mode)
        return None

    def melissa_fan_to_menuai(self, fan):
        """Translate Melissa fan modes to menuai modes."""
        if fan == self._api.FAN_AUTO:
            return FAN_AUTO
        if fan == self._api.FAN_LOW:
            return FAN_LOW
        if fan == self._api.FAN_MEDIUM:
            return FAN_MEDIUM
        if fan == self._api.FAN_HIGH:
            return FAN_HIGH
        _LOGGER.warning("Fan mode %s could not be mapped to menuai", fan)
        return None

    def menuai_mode_to_melissa(self, mode):
        """Translate menuai states to melissa modes."""
        if mode == HVACMode.HEAT:
            return self._api.MODE_HEAT
        if mode == HVACMode.COOL:
            return self._api.MODE_COOL
        if mode == HVACMode.DRY:
            return self._api.MODE_DRY
        if mode == HVACMode.FAN_ONLY:
            return self._api.MODE_FAN
        _LOGGER.warning("Melissa have no setting for %s mode", mode)
        return None

    def menuai_fan_to_melissa(self, fan):
        """Translate menuai fan modes to melissa modes."""
        if fan == FAN_AUTO:
            return self._api.FAN_AUTO
        if fan == FAN_LOW:
            return self._api.FAN_LOW
        if fan == FAN_MEDIUM:
            return self._api.FAN_MEDIUM
        if fan == FAN_HIGH:
            return self._api.FAN_HIGH
        _LOGGER.warning("Melissa have no setting for %s fan mode", fan)
        return None
