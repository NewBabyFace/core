"""Support for MenuAI Cloud binary sensors."""

from __future__ import annotations

import asyncio
from typing import Any

from menuai_nabucasa import Cloud

from menuai.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from menuai.config_entries import ConfigEntry
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .client import CloudClient
from .const import DATA_CLOUD, DISPATCHER_REMOTE_UPDATE

WAIT_UNTIL_CHANGE = 3


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the MenuAI Cloud binary sensors."""
    cloud = menuai.data[DATA_CLOUD]
    async_add_entities([CloudRemoteBinary(cloud)])


class CloudRemoteBinary(BinarySensorEntity):
    """Representation of an Cloud Remote UI Connection binary sensor."""

    _attr_name = "Remote UI"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_should_poll = False
    _attr_unique_id = "cloud-remote-ui-connectivity"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, cloud: Cloud[CloudClient]) -> None:
        """Initialize the binary sensor."""
        self.cloud = cloud

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.cloud.remote.is_connected

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.cloud.remote.certificate is not None

    async def async_added_to_menuai(self) -> None:
        """Register update dispatcher."""

        async def async_state_update(data: Any) -> None:
            """Update callback."""
            await asyncio.sleep(WAIT_UNTIL_CHANGE)
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(
                self.menuai, DISPATCHER_REMOTE_UPDATE, async_state_update
            )
        )
