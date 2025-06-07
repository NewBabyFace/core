"""Expose images as media sources."""

from __future__ import annotations

from typing import cast

from menuai.components.media_player import BrowseError, MediaClass
from menuai.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from menuai.const import ATTR_FRIENDLY_NAME
from menuai.core import menuai, State

from .const import DATA_COMPONENT, DOMAIN


async def async_get_media_source(menuai: menuai) -> ImageMediaSource:
    """Set up image media source."""
    return ImageMediaSource(menuai)


class ImageMediaSource(MediaSource):
    """Provide images as media sources."""

    name: str = "Image"

    def __init__(self, menuai: menuai) -> None:
        """Initialize ImageMediaSource."""
        super().__init__(DOMAIN)
        self.menuai = menuai

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve media to a url."""
        image = self.menuai.data[DATA_COMPONENT].get_entity(item.identifier)

        if not image:
            raise Unresolvable(f"Could not resolve media item: {item.identifier}")

        return PlayMedia(
            f"/api/image_proxy_stream/{image.entity_id}", image.content_type
        )

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        """Return media."""
        if item.identifier:
            raise BrowseError("Unknown item")

        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=image.entity_id,
                media_class=MediaClass.VIDEO,
                media_content_type=image.content_type,
                title=cast(State, self.menuai.states.get(image.entity_id)).attributes.get(
                    ATTR_FRIENDLY_NAME, image.name
                ),
                thumbnail=f"/api/image_proxy/{image.entity_id}",
                can_play=True,
                can_expand=False,
            )
            for image in self.menuai.data[DATA_COMPONENT].entities
        ]

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.APP,
            media_content_type="",
            title="Image",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.IMAGE,
            children=children,
        )
