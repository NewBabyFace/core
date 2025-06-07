"""Light support for switch entities."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from menuai.components.light import (
    PLATFORM_SCHEMA as LIGHT_PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    CONF_ENTITY_ID,
    CONF_NAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import Event, EventStateChangedData, menuai, callback
from menuai.helpers import config_validation as cv, entity_registry as er
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.event import async_track_state_change_event
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN

DEFAULT_NAME = "Light Switch"

PLATFORM_SCHEMA = LIGHT_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_ENTITY_ID): cv.entity_domain(DOMAIN),
    }
)


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Initialize Light Switch platform."""
    registry = er.async_get(menuai)
    wrapped_switch = registry.async_get(config[CONF_ENTITY_ID])
    unique_id = wrapped_switch.unique_id if wrapped_switch else None

    async_add_entities(
        [
            LightSwitch(
                config[CONF_NAME],
                config[CONF_ENTITY_ID],
                unique_id,
            )
        ]
    )


class LightSwitch(LightEntity):
    """Represents a Switch as a Light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_should_poll = False
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, name: str, switch_entity_id: str, unique_id: str | None) -> None:
        """Initialize Light Switch."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._switch_entity_id = switch_entity_id

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Forward the turn_on command to the switch in this light switch."""
        await self.menuai.services.async_call(
            DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self._switch_entity_id},
            blocking=True,
            context=self._context,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Forward the turn_off command to the switch in this light switch."""
        await self.menuai.services.async_call(
            DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self._switch_entity_id},
            blocking=True,
            context=self._context,
        )

    async def async_added_to_menuai(self) -> None:
        """Register callbacks."""

        @callback
        def async_state_changed_listener(
            event: Event[EventStateChangedData] | None = None,
        ) -> None:
            """Handle child updates."""
            if (
                state := self.menuai.states.get(self._switch_entity_id)
            ) is None or state.state == STATE_UNAVAILABLE:
                self._attr_available = False
                return
            self._attr_available = True
            self._attr_is_on = state.state == STATE_ON
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.menuai, [self._switch_entity_id], async_state_changed_listener
            )
        )
        # Call once on adding
        async_state_changed_listener()
