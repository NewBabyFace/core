"""Select platform for the Flipr's Hub."""

import logging

from menuai.components.select import SelectEntity, SelectEntityDescription
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FliprConfigEntry
from .entity import FliprEntity

_LOGGER = logging.getLogger(__name__)

SELECT_TYPES: tuple[SelectEntityDescription, ...] = (
    SelectEntityDescription(
        key="hubMode",
        translation_key="hub_mode",
        options=["auto", "manual", "planning"],
    ),
)


async def async_setup_entry(
    menuai: menuai,
    config_entry: FliprConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up select for Flipr hub mode."""
    coordinators = config_entry.runtime_data.hub_coordinators

    async_add_entities(
        FliprHubSelect(coordinator, description, True)
        for description in SELECT_TYPES
        for coordinator in coordinators
    )


class FliprHubSelect(FliprEntity, SelectEntity):
    """Select representing Hub mode."""

    @property
    def current_option(self) -> str | None:
        """Return current select option."""
        _LOGGER.debug("coordinator data = %s", self.coordinator.data)
        return self.coordinator.data["mode"]

    async def async_select_option(self, option: str) -> None:
        """Select new mode for Hub."""
        _LOGGER.debug("Changing mode of %s to %s", self.device_id, option)
        data = await self.menuai.async_add_executor_job(
            self.coordinator.client.set_hub_mode,
            self.device_id,
            option,
        )
        _LOGGER.debug("New hub infos are %s", data)
        self.coordinator.async_set_updated_data(data)
