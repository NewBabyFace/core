"""Support for interacting with UpCloud servers."""

from typing import Any

from menuai.components.switch import SwitchEntity
from menuai.const import STATE_OFF
from menuai.core import menuai
from menuai.helpers.dispatcher import dispatcher_send
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import UpCloudConfigEntry
from .entity import UpCloudServerEntity

SIGNAL_UPDATE_UPCLOUD = "upcloud_update"


async def async_setup_entry(
    menuai: menuai,
    config_entry: UpCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the UpCloud server switch."""
    coordinator = config_entry.runtime_data
    entities = [UpCloudSwitch(config_entry, uuid) for uuid in coordinator.data]
    async_add_entities(entities, True)


class UpCloudSwitch(UpCloudServerEntity, SwitchEntity):
    """Representation of an UpCloud server switch."""

    def turn_on(self, **kwargs: Any) -> None:
        """Start the server."""
        if self.state == STATE_OFF:
            self._server.start()
            dispatcher_send(self.menuai, SIGNAL_UPDATE_UPCLOUD)

    def turn_off(self, **kwargs: Any) -> None:
        """Stop the server."""
        if self.is_on:
            self._server.stop()
