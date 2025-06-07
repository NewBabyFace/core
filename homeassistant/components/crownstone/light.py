"""Support for Crownstone devices."""

from __future__ import annotations

from functools import partial
from typing import Any

from crownstone_cloud.cloud_models.crownstones import Crownstone
from crownstone_cloud.const import DIMMING_ABILITY
from crownstone_cloud.exceptions import CrownstoneAbilityError
from crownstone_uart import CrownstoneUart

from menuai.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CROWNSTONE_INCLUDE_TYPES,
    CROWNSTONE_SUFFIX,
    SIG_CROWNSTONE_STATE_UPDATE,
    SIG_UART_STATE_CHANGE,
)
from .entity import CrownstoneEntity
from .entry_manager import CrownstoneConfigEntry
from .helpers import map_from_to


async def async_setup_entry(
    menuai: menuai,
    config_entry: CrownstoneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up crownstones from a config entry."""
    manager = config_entry.runtime_data

    entities: list[CrownstoneLightEntity] = []

    # Add Crownstone entities that support switching/dimming
    for sphere in manager.cloud.cloud_data:
        for crownstone in sphere.crownstones:
            if crownstone.type in CROWNSTONE_INCLUDE_TYPES:
                # Crownstone can communicate with Crownstone USB
                if manager.uart and sphere.cloud_id == manager.usb_sphere_id:
                    entities.append(CrownstoneLightEntity(crownstone, manager.uart))
                # Crownstone can't communicate with Crownstone USB
                else:
                    entities.append(CrownstoneLightEntity(crownstone))

    async_add_entities(entities)


def crownstone_state_to_menuai(value: int) -> int:
    """Crownstone 0..100 to menuai 0..255."""
    return map_from_to(value, 0, 100, 0, 255)


def menuai_to_crownstone_state(value: int) -> int:
    """menuai 0..255 to Crownstone 0..100."""
    return map_from_to(value, 0, 255, 0, 100)


class CrownstoneLightEntity(CrownstoneEntity, LightEntity):
    """Representation of a crownstone.

    Light platform is used to support dimming.
    """

    _attr_name = None
    _attr_translation_key = "german_power_outlet"

    def __init__(
        self, crownstone_data: Crownstone, usb: CrownstoneUart | None = None
    ) -> None:
        """Initialize the crownstone."""
        super().__init__(crownstone_data)
        self.usb = usb
        # Entity class attributes
        self._attr_unique_id = f"{self.cloud_id}-{CROWNSTONE_SUFFIX}"

    @property
    def brightness(self) -> int | None:
        """Return the brightness if dimming enabled."""
        return crownstone_state_to_menuai(self.device.state)

    @property
    def is_on(self) -> bool:
        """Return if the device is on."""
        return crownstone_state_to_menuai(self.device.state) > 0

    @property
    def color_mode(self) -> str:
        """Return the color mode of the light."""
        if self.device.abilities.get(DIMMING_ABILITY).is_enabled:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[str] | None:
        """Flag supported color modes."""
        return {self.color_mode}

    async def async_added_to_menuai(self) -> None:
        """Set up a listener when this entity is added to HA."""
        # new state received
        self.async_on_remove(
            async_dispatcher_connect(
                self.menuai, SIG_CROWNSTONE_STATE_UPDATE, self.async_write_ha_state
            )
        )
        # updates state attributes when usb connects/disconnects
        self.async_on_remove(
            async_dispatcher_connect(
                self.menuai, SIG_UART_STATE_CHANGE, self.async_write_ha_state
            )
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on this light via dongle or cloud."""
        if ATTR_BRIGHTNESS in kwargs:
            if self.usb is not None and self.usb.is_ready():
                await self.menuai.async_add_executor_job(
                    partial(
                        self.usb.dim_crownstone,
                        self.device.unique_id,
                        menuai_to_crownstone_state(kwargs[ATTR_BRIGHTNESS]),
                    )
                )
            else:
                try:
                    await self.device.async_set_brightness(
                        menuai_to_crownstone_state(kwargs[ATTR_BRIGHTNESS])
                    )
                except CrownstoneAbilityError as ability_error:
                    raise menuaiError(ability_error) from ability_error

            # assume brightness is set on device
            self.device.state = menuai_to_crownstone_state(kwargs[ATTR_BRIGHTNESS])
            self.async_write_ha_state()

        elif self.usb is not None and self.usb.is_ready():
            await self.menuai.async_add_executor_job(
                partial(self.usb.switch_crownstone, self.device.unique_id, on=True)
            )
            self.device.state = 100
            self.async_write_ha_state()

        else:
            await self.device.async_turn_on()
            self.device.state = 100
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off this device via dongle or cloud."""
        if self.usb is not None and self.usb.is_ready():
            await self.menuai.async_add_executor_job(
                partial(self.usb.switch_crownstone, self.device.unique_id, on=False)
            )

        else:
            await self.device.async_turn_off()

        self.device.state = 0
        self.async_write_ha_state()
