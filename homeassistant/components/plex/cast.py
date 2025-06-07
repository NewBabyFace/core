"""Google Cast support for the Plex component."""

from __future__ import annotations

from pychromecast import Chromecast
from pychromecast.controllers.plex import PlexController

from menuai.components.cast import DOMAIN as CAST_DOMAIN
from menuai.components.media_player import BrowseMedia, MediaClass, MediaType
from menuai.core import menuai

from . import async_browse_media as async_browse_plex_media, is_plex_media_id
from .services import process_plex_payload


async def async_get_media_browser_root_object(
    menuai: menuai, cast_type: str
) -> list[BrowseMedia]:
    """Create a root object for media browsing."""
    return [
        BrowseMedia(
            title="Plex",
            media_class=MediaClass.APP,
            media_content_id="",
            media_content_type="plex",
            thumbnail="https://brands.home-assistant.io/_/plex/logo.png",
            can_play=False,
            can_expand=True,
        )
    ]


async def async_browse_media(
    menuai: menuai,
    media_content_type: MediaType | str,
    media_content_id: str,
    cast_type: str,
) -> BrowseMedia | None:
    """Browse media."""
    if is_plex_media_id(media_content_id):
        return await async_browse_plex_media(
            menuai, media_content_type, media_content_id, platform=CAST_DOMAIN
        )
    if media_content_type == "plex":
        return await async_browse_plex_media(menuai, None, None, platform=CAST_DOMAIN)
    return None


def _play_media(
    menuai: menuai, chromecast: Chromecast, media_type: str, media_id: str
) -> None:
    """Play media."""
    result = process_plex_payload(menuai, media_type, media_id)
    controller = PlexController()
    chromecast.register_handler(controller)
    offset_in_s = result.offset / 1000
    controller.play_media(result.media, offset=offset_in_s)


async def async_play_media(
    menuai: menuai,
    cast_entity_id: str,
    chromecast: Chromecast,
    media_type: MediaType | str,
    media_id: str,
) -> bool:
    """Play media."""
    if is_plex_media_id(media_id):
        await menuai.async_add_executor_job(
            _play_media, menuai, chromecast, media_type, media_id
        )
        return True

    return False
