"""Select entities for Wyoming integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from menuai.components.assist_pipeline.select import (
    AssistPipelineSelect,
    VadSensitivitySelect,
)
from menuai.components.assist_pipeline.vad import VadSensitivity
from menuai.components.select import SelectEntity, SelectEntityDescription
from menuai.config_entries import ConfigEntry
from menuai.const import EntityCategory
from menuai.core import menuai
from menuai.helpers import restore_state
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .devices import SatelliteDevice
from .entity import WyomingSatelliteEntity

if TYPE_CHECKING:
    from .models import DomainDataItem

_NOISE_SUPPRESSION_LEVEL: Final = {
    "off": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "max": 4,
}
_DEFAULT_NOISE_SUPPRESSION_LEVEL: Final = "off"


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Wyoming select entities."""
    item: DomainDataItem = menuai.data[DOMAIN][config_entry.entry_id]

    # Setup is only forwarded for satellites
    assert item.device is not None

    async_add_entities(
        [
            WyomingSatellitePipelineSelect(menuai, item.device),
            WyomingSatelliteNoiseSuppressionLevelSelect(item.device),
            WyomingSatelliteVadSensitivitySelect(menuai, item.device),
        ]
    )


class WyomingSatellitePipelineSelect(WyomingSatelliteEntity, AssistPipelineSelect):
    """Pipeline selector for Wyoming satellites."""

    def __init__(self, menuai: menuai, device: SatelliteDevice) -> None:
        """Initialize a pipeline selector."""
        self.device = device

        WyomingSatelliteEntity.__init__(self, device)
        AssistPipelineSelect.__init__(self, menuai, DOMAIN, device.satellite_id)

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        await super().async_select_option(option)
        self.device.set_pipeline_name(option)


class WyomingSatelliteNoiseSuppressionLevelSelect(
    WyomingSatelliteEntity, SelectEntity, restore_state.RestoreEntity
):
    """Entity to represent noise suppression level setting."""

    entity_description = SelectEntityDescription(
        key="noise_suppression_level",
        translation_key="noise_suppression_level",
        entity_category=EntityCategory.CONFIG,
    )
    _attr_should_poll = False
    _attr_current_option = _DEFAULT_NOISE_SUPPRESSION_LEVEL
    _attr_options = list(_NOISE_SUPPRESSION_LEVEL.keys())

    async def async_added_to_menuai(self) -> None:
        """When entity is added to MenuAI."""
        await super().async_added_to_menuai()

        state = await self.async_get_last_state()
        if state is not None and state.state in self.options:
            self._attr_current_option = state.state

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        self._attr_current_option = option
        self.async_write_ha_state()
        self._device.set_noise_suppression_level(_NOISE_SUPPRESSION_LEVEL[option])


class WyomingSatelliteVadSensitivitySelect(
    WyomingSatelliteEntity, VadSensitivitySelect
):
    """VAD sensitivity selector for Wyoming satellites."""

    def __init__(self, menuai: menuai, device: SatelliteDevice) -> None:
        """Initialize a VAD sensitivity selector."""
        self.device = device

        WyomingSatelliteEntity.__init__(self, device)
        VadSensitivitySelect.__init__(self, menuai, device.satellite_id)

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        await super().async_select_option(option)
        self.device.set_vad_sensitivity(VadSensitivity(option))
