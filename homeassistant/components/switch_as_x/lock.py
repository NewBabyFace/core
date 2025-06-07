"""Lock support for switch entities."""

from __future__ import annotations

from typing import Any

from menuai.components.lock import DOMAIN as LOCK_DOMAIN, LockEntity
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.const import (
    ATTR_ENTITY_ID,
    CONF_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from menuai.core import Event, EventStateChangedData, menuai, callback
from menuai.helpers import entity_registry as er
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_INVERT
from .entity import BaseInvertableEntity


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize Lock Switch config entry."""
    registry = er.async_get(menuai)
    entity_id = er.async_validate_entity_id(
        registry, config_entry.options[CONF_ENTITY_ID]
    )

    async_add_entities(
        [
            LockSwitch(
                menuai,
                config_entry.title,
                LOCK_DOMAIN,
                config_entry.options[CONF_INVERT],
                entity_id,
                config_entry.entry_id,
            )
        ]
    )


class LockSwitch(BaseInvertableEntity, LockEntity):
    """Represents a Switch as a Lock."""

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self.menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON if self._invert_state else SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self._switch_entity_id},
            blocking=True,
            context=self._context,
        )

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self.menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF if self._invert_state else SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self._switch_entity_id},
            blocking=True,
            context=self._context,
        )

    @callback
    def async_state_changed_listener(
        self, event: Event[EventStateChangedData] | None = None
    ) -> None:
        """Handle child updates."""
        super().async_state_changed_listener(event)
        if (
            not self.available
            or (state := self.menuai.states.get(self._switch_entity_id)) is None
        ):
            return

        # Logic is the same as the lock device class for binary sensors
        # on means open (unlocked), off means closed (locked)
        if self._invert_state:
            self._attr_is_locked = state.state == STATE_ON
        else:
            self._attr_is_locked = state.state != STATE_ON
