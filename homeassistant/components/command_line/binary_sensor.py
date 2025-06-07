"""Support for custom shell commands to retrieve values."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from menuai.components.binary_sensor import BinarySensorEntity
from menuai.const import (
    CONF_COMMAND,
    CONF_NAME,
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
    CONF_SCAN_INTERVAL,
    CONF_VALUE_TEMPLATE,
)
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.event import async_track_time_interval
from menuai.helpers.template import Template
from menuai.helpers.trigger_template_entity import (
    ManualTriggerEntity,
    ValueTemplate,
)
from menuai.helpers.typing import ConfigType, DiscoveryInfoType
from menuai.util import dt as dt_util

from .const import CONF_COMMAND_TIMEOUT, LOGGER, TRIGGER_ENTITY_OPTIONS
from .sensor import CommandSensorData

DEFAULT_NAME = "Binary Command Sensor"
DEFAULT_PAYLOAD_ON = "ON"
DEFAULT_PAYLOAD_OFF = "OFF"

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Command line Binary Sensor."""
    if not discovery_info:
        return

    binary_sensor_config = discovery_info
    command: str = binary_sensor_config[CONF_COMMAND]
    payload_off: str = binary_sensor_config[CONF_PAYLOAD_OFF]
    payload_on: str = binary_sensor_config[CONF_PAYLOAD_ON]
    command_timeout: int = binary_sensor_config[CONF_COMMAND_TIMEOUT]
    scan_interval: timedelta = binary_sensor_config.get(
        CONF_SCAN_INTERVAL, SCAN_INTERVAL
    )
    value_template: ValueTemplate | None = binary_sensor_config.get(CONF_VALUE_TEMPLATE)

    data = CommandSensorData(menuai, command, command_timeout)

    trigger_entity_config = {
        CONF_NAME: Template(binary_sensor_config.get(CONF_NAME, DEFAULT_NAME), menuai),
        **{
            k: v for k, v in binary_sensor_config.items() if k in TRIGGER_ENTITY_OPTIONS
        },
    }

    async_add_entities(
        [
            CommandBinarySensor(
                data,
                trigger_entity_config,
                payload_on,
                payload_off,
                value_template,
                scan_interval,
            )
        ],
    )


class CommandBinarySensor(ManualTriggerEntity, BinarySensorEntity):
    """Representation of a command line binary sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        data: CommandSensorData,
        config: ConfigType,
        payload_on: str,
        payload_off: str,
        value_template: ValueTemplate | None,
        scan_interval: timedelta,
    ) -> None:
        """Initialize the Command line binary sensor."""
        super().__init__(self.menuai, config)
        self.data = data
        self._attr_is_on = None
        self._payload_on = payload_on
        self._payload_off = payload_off
        self._value_template = value_template
        self._scan_interval = scan_interval
        self._process_updates: asyncio.Lock | None = None

    async def async_added_to_menuai(self) -> None:
        """Call when entity about to be added to menuai."""
        await super().async_added_to_menuai()
        await self._update_entity_state()
        self.async_on_remove(
            async_track_time_interval(
                self.menuai,
                self._update_entity_state,
                self._scan_interval,
                name=f"Command Line Binary Sensor - {self.name}",
                cancel_on_shutdown=True,
            ),
        )

    async def _update_entity_state(self, now: datetime | None = None) -> None:
        """Update the state of the entity."""
        if self._process_updates is None:
            self._process_updates = asyncio.Lock()
        if self._process_updates.locked():
            LOGGER.warning(
                "Updating Command Line Binary Sensor %s took longer than the scheduled update interval %s",
                self.name,
                self._scan_interval,
            )
            return

        async with self._process_updates:
            await self._async_update()

    async def _async_update(self) -> None:
        """Get the latest data and updates the state."""
        await self.data.async_update()
        value = self.data.value

        variables = self._template_variables_with_value(value)
        if not self._render_availability_template(variables):
            self.async_write_ha_state()
            return

        if self._value_template is not None:
            value = self._value_template.async_render_as_value_template(
                self.entity_id, variables, None
            )
        self._attr_is_on = None
        if value == self._payload_on:
            self._attr_is_on = True
        elif value == self._payload_off:
            self._attr_is_on = False

        self._process_manual_data(variables)
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """
        await self._update_entity_state(dt_util.now())
