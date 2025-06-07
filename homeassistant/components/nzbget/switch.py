"""Support for NZBGet switches."""

from __future__ import annotations

from typing import Any

from menuai.components.switch import SwitchEntity
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_NAME
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import NZBGetDataUpdateCoordinator
from .entity import NZBGetEntity


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NZBGet sensor based on a config entry."""
    coordinator: NZBGetDataUpdateCoordinator = menuai.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    switches = [
        NZBGetDownloadSwitch(
            coordinator,
            entry.entry_id,
            entry.data[CONF_NAME],
        ),
    ]

    async_add_entities(switches)


class NZBGetDownloadSwitch(NZBGetEntity, SwitchEntity):
    """Representation of a NZBGet download switch."""

    _attr_translation_key = "download"

    def __init__(
        self,
        coordinator: NZBGetDataUpdateCoordinator,
        entry_id: str,
        entry_name: str,
    ) -> None:
        """Initialize a new NZBGet switch."""
        self._attr_unique_id = f"{entry_id}_download"

        super().__init__(
            coordinator=coordinator,
            entry_id=entry_id,
            entry_name=entry_name,
        )

    @property
    def is_on(self):
        """Return the state of the switch."""
        return not self.coordinator.data["status"].get("DownloadPaused", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set downloads to enabled."""
        await self.menuai.async_add_executor_job(self.coordinator.nzbget.resumedownload)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Set downloads to paused."""
        await self.menuai.async_add_executor_job(self.coordinator.nzbget.pausedownload)
        await self.coordinator.async_request_refresh()
