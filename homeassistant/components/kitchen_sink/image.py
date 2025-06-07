"""Demo image platform."""

from __future__ import annotations

from pathlib import Path

from menuai.components.image import ImageEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from menuai.helpers.typing import ConfigType, DiscoveryInfoType
from menuai.util import dt as dt_util


async def async_setup_platform(
    menuai: menuai,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up image entities."""
    async_add_entities(
        [
            DemoImage(
                menuai,
                "kitchen_sink_image_001",
                "QR Code",
                "image/png",
                "qr_code.png",
            ),
        ]
    )


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Everything but the Kitchen Sink config entry."""
    await async_setup_platform(menuai, {}, async_add_entities)


class DemoImage(ImageEntity):
    """Representation of an image entity."""

    def __init__(
        self,
        menuai: menuai,
        unique_id: str,
        name: str,
        content_type: str,
        image: str,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(menuai)
        self._attr_content_type = content_type
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._image_filename = image

    async def async_added_to_menuai(self):
        """Set the update time."""
        self._attr_image_last_updated = dt_util.utcnow()

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        image_path = Path(__file__).parent / self._image_filename
        return await self.menuai.async_add_executor_job(image_path.read_bytes)
