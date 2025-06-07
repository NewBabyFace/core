"""Camera support for the Skybell HD Doorbell."""

from __future__ import annotations

from aiohttp import web
from haffmpeg.camera import CameraMjpeg

from menuai.components.camera import Camera, CameraEntityDescription
from menuai.components.ffmpeg import get_ffmpeg_manager
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_aiohttp_proxy_stream
from menuai.helpers.entity import EntityDescription
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import SkybellDataUpdateCoordinator
from .entity import SkybellEntity

CAMERA_TYPES: tuple[CameraEntityDescription, ...] = (
    CameraEntityDescription(
        key="activity",
        translation_key="activity",
    ),
    CameraEntityDescription(
        key="avatar",
        translation_key="camera",
    ),
)


async def async_setup_entry(
    menuai: menuai,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Skybell camera."""
    entities = []
    for description in CAMERA_TYPES:
        for coordinator in menuai.data[DOMAIN][entry.entry_id]:
            if description.key == "avatar":
                entities.append(SkybellCamera(coordinator, description))
            else:
                entities.append(SkybellActivityCamera(coordinator, description))
    async_add_entities(entities)


class SkybellCamera(SkybellEntity, Camera):
    """A camera implementation for Skybell devices."""

    def __init__(
        self,
        coordinator: SkybellDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize a camera for a Skybell device."""
        super().__init__(coordinator, description)
        Camera.__init__(self)

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Get the latest camera image."""
        return self._device.images[self.entity_description.key]


class SkybellActivityCamera(SkybellCamera):
    """A camera implementation for latest Skybell activity."""

    async def handle_async_mjpeg_stream(
        self, request: web.Request
    ) -> web.StreamResponse:
        """Generate an HTTP MJPEG stream from the latest recorded activity."""
        stream = CameraMjpeg(get_ffmpeg_manager(self.menuai).binary)
        url = await self.coordinator.device.async_get_activity_video_url()
        await stream.open_camera(url, extra_cmd="-r 210")

        try:
            return await async_aiohttp_proxy_stream(
                self.menuai,
                request,
                await stream.get_reader(),
                get_ffmpeg_manager(self.menuai).ffmpeg_stream_content_type,
            )
        finally:
            await stream.close()
