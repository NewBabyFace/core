"""Component to embed Google Cast."""

from __future__ import annotations

from typing import Protocol

from pychromecast import Chromecast

from menuai.components.media_player import BrowseMedia, MediaType
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai, callback
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr
from menuai.helpers.integration_platform import (
    async_process_integration_platforms,
)

from . import home_assistant_cast
from .const import DOMAIN

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Cast from a config entry."""
    menuai.data[DOMAIN] = {"cast_platform": {}, "unknown_models": {}}
    await home_assistant_cast.async_setup_ha_cast(menuai, entry)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_process_integration_platforms(menuai, DOMAIN, _register_cast_platform)
    return True


class CastProtocol(Protocol):
    """Define the format of cast platforms."""

    async def async_get_media_browser_root_object(
        self, menuai: menuai, cast_type: str
    ) -> list[BrowseMedia]:
        """Create a list of root objects for media browsing."""

    async def async_browse_media(
        self,
        menuai: menuai,
        media_content_type: MediaType | str,
        media_content_id: str,
        cast_type: str,
    ) -> BrowseMedia | None:
        """Browse media.

        Return a BrowseMedia object or None if the media does not belong to
        this platform.
        """

    async def async_play_media(
        self,
        menuai: menuai,
        cast_entity_id: str,
        chromecast: Chromecast,
        media_type: MediaType | str,
        media_id: str,
    ) -> bool:
        """Play media.

        Return True if the media is played by the platform, False if not.
        """


@callback
def _register_cast_platform(
    menuai: menuai, integration_domain: str, platform: CastProtocol
):
    """Register a cast platform."""
    if (
        not hasattr(platform, "async_get_media_browser_root_object")
        or not hasattr(platform, "async_browse_media")
        or not hasattr(platform, "async_play_media")
    ):
        raise menuaiError(f"Invalid cast platform {platform}")
    menuai.data[DOMAIN]["cast_platform"][integration_domain] = platform


async def async_remove_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Remove MenuAI Cast user."""
    await home_assistant_cast.async_remove_user(menuai, entry)


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove cast config entry from a device.

    The actual cleanup is done in CastMediaPlayerEntity.async_will_remove_from_menuai.
    """
    return True
