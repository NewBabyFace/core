"""Support for ZoneMinder camera streaming."""

from __future__ import annotations

import logging

from zoneminder.monitor import Monitor
from zoneminder.zm import ZoneMinder

from menuai.components.mjpeg import MjpegCamera, filter_urllib3_logging
from menuai.core import menuai
from menuai.exceptions import PlatformNotReady
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


def setup_platform(
    menuai: menuai,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the ZoneMinder cameras."""
    filter_urllib3_logging()
    cameras = []
    zm_client: ZoneMinder
    for zm_client in menuai.data[DOMAIN].values():
        if not (monitors := zm_client.get_monitors()):
            raise PlatformNotReady(
                "Camera could not fetch any monitors from ZoneMinder"
            )

        for monitor in monitors:
            _LOGGER.debug("Initializing camera %s", monitor.id)
            cameras.append(ZoneMinderCamera(monitor, zm_client.verify_ssl))
    add_entities(cameras)


class ZoneMinderCamera(MjpegCamera):
    """Representation of a ZoneMinder Monitor Stream."""

    _attr_should_poll = True  # Cameras default to False

    def __init__(self, monitor: Monitor, verify_ssl: bool) -> None:
        """Initialize as a subclass of MjpegCamera."""
        super().__init__(
            name=monitor.name,
            mjpeg_url=monitor.mjpeg_image_url,
            still_image_url=monitor.still_image_url,
            verify_ssl=verify_ssl,
        )
        self._attr_is_recording = False
        self._attr_available = False
        self._monitor = monitor

    def update(self) -> None:
        """Update our recording state from the ZM API."""
        _LOGGER.debug("Updating camera state for monitor %i", self._monitor.id)
        self._attr_is_recording = self._monitor.is_recording
        self._attr_available = self._monitor.is_available
