"""Camera helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from menuai.core import menuai
from menuai.exceptions import menuaiError

from .const import DATA_COMPONENT

if TYPE_CHECKING:
    from . import Camera


def get_camera_from_entity_id(menuai: menuai, entity_id: str) -> Camera:
    """Get camera component from entity_id."""
    component = menuai.data.get(DATA_COMPONENT)
    if component is None:
        raise menuaiError("Camera integration not set up")

    if (camera := component.get_entity(entity_id)) is None:
        raise menuaiError("Camera not found")

    if not camera.is_on:
        raise menuaiError("Camera is off")

    return camera
