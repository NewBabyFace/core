"""Constants for the image integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from menuai.helpers.entity_component import EntityComponent

    from . import ImageEntity


DOMAIN: Final = "image"
DATA_COMPONENT: menuaiKey[EntityComponent[ImageEntity]] = menuaiKey(DOMAIN)

IMAGE_TIMEOUT: Final = 10
