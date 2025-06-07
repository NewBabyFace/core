"""Constants for the menuai integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from menuai import core as ha
from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from .exposed_entities import ExposedEntities

DOMAIN = ha.DOMAIN

DATA_EXPOSED_ENTITIES: menuaiKey[ExposedEntities] = menuaiKey(f"{DOMAIN}.exposed_entites")
DATA_STOP_HANDLER = f"{DOMAIN}.stop_handler"

SERVICE_menuai_STOP: Final = "stop"
SERVICE_menuai_RESTART: Final = "restart"
