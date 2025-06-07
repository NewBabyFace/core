"""Support for Freedompro lock."""

import json
from typing import Any

from pyfreedompro import put_state

from menuai.components.lock import LockEntity
from menuai.const import CONF_API_KEY
from menuai.core import menuai, callback
from menuai.helpers import aiohttp_client
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback
from menuai.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FreedomproConfigEntry, FreedomproDataUpdateCoordinator


async def async_setup_entry(
    menuai: menuai,
    entry: FreedomproConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Freedompro lock."""
    api_key: str = entry.data[CONF_API_KEY]
    coordinator = entry.runtime_data
    async_add_entities(
        Device(menuai, api_key, device, coordinator)
        for device in coordinator.data
        if device["type"] == "lock"
    )


class Device(CoordinatorEntity[FreedomproDataUpdateCoordinator], LockEntity):
    """Representation of a Freedompro lock."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        menuai: menuai,
        api_key: str,
        device: dict[str, Any],
        coordinator: FreedomproDataUpdateCoordinator,
    ) -> None:
        """Initialize the Freedompro lock."""
        super().__init__(coordinator)
        self._menuai = menuai
        self._session = aiohttp_client.async_get_clientsession(self._menuai)
        self._api_key = api_key
        self._attr_unique_id = device["uid"]
        self._type = device["type"]
        self._characteristics = device["characteristics"]
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, device["uid"]),
            },
            manufacturer="Freedompro",
            model=self._type,
            name=device["name"],
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        device = next(
            (
                device
                for device in self.coordinator.data
                if device["uid"] == self.unique_id
            ),
            None,
        )
        if device is not None and "state" in device:
            state = device["state"]
            if "lock" in state:
                if state["lock"] == 1:
                    self._attr_is_locked = True
                else:
                    self._attr_is_locked = False
        super()._handle_coordinator_update()

    async def async_added_to_menuai(self) -> None:
        """When entity is added to menuai."""
        await super().async_added_to_menuai()
        self._handle_coordinator_update()

    async def async_lock(self, **kwargs: Any) -> None:
        """Async function to lock the lock."""
        payload = {"lock": 1}
        await put_state(
            self._session,
            self._api_key,
            self.unique_id,
            json.dumps(payload),
        )
        await self.coordinator.async_request_refresh()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Async function to unlock the lock."""
        payload = {"lock": 0}
        await put_state(
            self._session,
            self._api_key,
            self.unique_id,
            json.dumps(payload),
        )
        await self.coordinator.async_request_refresh()
