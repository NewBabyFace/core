"""Support for Lutron Homeworks buttons."""

from __future__ import annotations

import asyncio

from pyhomeworks.pyhomeworks import Homeworks

from menuai.components.button import ButtonEntity
from menuai.const import CONF_NAME
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HomeworksConfigEntry
from .const import (
    CONF_ADDR,
    CONF_BUTTONS,
    CONF_CONTROLLER_ID,
    CONF_KEYPADS,
    CONF_NUMBER,
    CONF_RELEASE_DELAY,
    DOMAIN,
)
from .entity import HomeworksEntity


async def async_setup_entry(
    menuai: menuai,
    entry: HomeworksConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Homeworks buttons."""
    controller = entry.runtime_data.controller
    controller_id = entry.options[CONF_CONTROLLER_ID]
    entities = []
    for keypad in entry.options.get(CONF_KEYPADS, []):
        for button in keypad[CONF_BUTTONS]:
            entity = HomeworksButton(
                controller,
                controller_id,
                keypad[CONF_ADDR],
                keypad[CONF_NAME],
                button[CONF_NAME],
                button[CONF_NUMBER],
                button[CONF_RELEASE_DELAY],
            )
            entities.append(entity)
    async_add_entities(entities, True)


class HomeworksButton(HomeworksEntity, ButtonEntity):
    """Homeworks Button."""

    def __init__(
        self,
        controller: Homeworks,
        controller_id: str,
        addr: str,
        keypad_name: str,
        button_name: str,
        button_number: int,
        release_delay: float,
    ) -> None:
        """Create device with Addr, name, and rate."""
        super().__init__(controller, controller_id, addr, button_number, button_name)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{controller_id}.{addr}")}, name=keypad_name
        )
        self._release_delay = release_delay

    async def async_press(self) -> None:
        """Press the button."""
        await self.menuai.async_add_executor_job(
            self._controller._send,  # noqa: SLF001
            f"KBP, {self._addr}, {self._idx}",
        )
        if not self._release_delay:
            return
        await asyncio.sleep(self._release_delay)
        await self.menuai.async_add_executor_job(
            self._controller._send,  # noqa: SLF001
            f"KBR, {self._addr}, {self._idx}",
        )
