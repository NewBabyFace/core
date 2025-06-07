"""Select entities for VoIP integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from menuai.components.assist_pipeline.select import (
    AssistPipelineSelect,
    VadSensitivitySelect,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .devices import VoIPDevice
from .entity import VoIPEntity

if TYPE_CHECKING:
    from . import DomainData


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up VoIP switch entities."""
    domain_data: DomainData = menuai.data[DOMAIN]

    @callback
    def async_add_device(device: VoIPDevice) -> None:
        """Add device."""
        async_add_entities(
            [VoipPipelineSelect(menuai, device), VoipVadSensitivitySelect(menuai, device)]
        )

    domain_data.devices.async_add_new_device_listener(async_add_device)

    entities: list[VoIPEntity] = []
    for device in domain_data.devices:
        entities.append(VoipPipelineSelect(menuai, device))
        entities.append(VoipVadSensitivitySelect(menuai, device))

    async_add_entities(entities)


class VoipPipelineSelect(VoIPEntity, AssistPipelineSelect):
    """Pipeline selector for VoIP devices."""

    def __init__(self, menuai: menuai, device: VoIPDevice) -> None:
        """Initialize a pipeline selector."""
        VoIPEntity.__init__(self, device)
        AssistPipelineSelect.__init__(self, menuai, DOMAIN, device.voip_id)


class VoipVadSensitivitySelect(VoIPEntity, VadSensitivitySelect):
    """VAD sensitivity selector for VoIP devices."""

    def __init__(self, menuai: menuai, device: VoIPDevice) -> None:
        """Initialize a VAD sensitivity selector."""
        VoIPEntity.__init__(self, device)
        VadSensitivitySelect.__init__(self, menuai, device.voip_id)
