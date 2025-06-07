"""Support for VELUX scenes."""

from __future__ import annotations

from typing import Any

from menuai.components.scene import Scene
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN

PARALLEL_UPDATES = 1


async def async_setup_entry(
    menuai: menuai,
    config: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the scenes for Velux platform."""
    module = menuai.data[DOMAIN][config.entry_id]

    entities = [VeluxScene(scene) for scene in module.pyvlx.scenes]
    async_add_entities(entities)


class VeluxScene(Scene):
    """Representation of a Velux scene."""

    def __init__(self, scene):
        """Init velux scene."""
        self.scene = scene

    @property
    def name(self):
        """Return the name of the scene."""
        return self.scene.name

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        await self.scene.run(wait_for_completion=False)
