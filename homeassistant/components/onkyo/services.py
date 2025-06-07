"""Onkyo services."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol

from menuai.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai, ServiceCall
from menuai.helpers import config_validation as cv
from menuai.util.menuai_dict import menuaiKey

from .const import DOMAIN

if TYPE_CHECKING:
    from .media_player import OnkyoMediaPlayer

DATA_MP_ENTITIES: menuaiKey[dict[str, dict[str, OnkyoMediaPlayer]]] = menuaiKey(DOMAIN)

ATTR_HDMI_OUTPUT = "hdmi_output"
ACCEPTED_VALUES = [
    "no",
    "analog",
    "yes",
    "out",
    "out-sub",
    "sub",
    "hdbaset",
    "both",
    "up",
]
ONKYO_SELECT_OUTPUT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_HDMI_OUTPUT): vol.In(ACCEPTED_VALUES),
    }
)
SERVICE_SELECT_HDMI_OUTPUT = "onkyo_select_hdmi_output"


def async_setup_services(menuai: menuai) -> None:
    """Register Onkyo services."""

    menuai.data.setdefault(DATA_MP_ENTITIES, {})

    async def async_service_handle(service: ServiceCall) -> None:
        """Handle for services."""
        entity_ids = service.data[ATTR_ENTITY_ID]

        targets: list[OnkyoMediaPlayer] = []
        for receiver_entities in menuai.data[DATA_MP_ENTITIES].values():
            targets.extend(
                entity
                for entity in receiver_entities.values()
                if entity.entity_id in entity_ids
            )

        for target in targets:
            if service.service == SERVICE_SELECT_HDMI_OUTPUT:
                await target.async_select_output(service.data[ATTR_HDMI_OUTPUT])

    menuai.services.async_register(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_SELECT_HDMI_OUTPUT,
        async_service_handle,
        schema=ONKYO_SELECT_OUTPUT_SCHEMA,
    )
