"""Test image media source."""

import pytest

from menuai.components import media_source
from menuai.core import menuai
from menuai.setup import async_setup_component


@pytest.fixture(autouse=True)
async def setup_media_source(menuai: menuai) -> None:
    """Set up media source."""
    assert await async_setup_component(menuai, "media_source", {})


async def test_browsing(menuai: menuai, mock_image_platform) -> None:
    """Test browsing image media source."""
    item = await media_source.async_browse_media(menuai, "media-source://image")
    assert item is not None
    assert item.title == "Image"
    assert len(item.children) == 1
    assert item.children[0].media_content_type == "image/jpeg"


async def test_resolving(menuai: menuai, mock_image_platform) -> None:
    """Test resolving."""
    item = await media_source.async_resolve_media(
        menuai, "media-source://image/image.test", None
    )
    assert item is not None
    assert item.url == "/api/image_proxy_stream/image.test"
    assert item.mime_type == "image/jpeg"


async def test_resolving_non_existing_camera(
    menuai: menuai, mock_image_platform
) -> None:
    """Test resolving."""
    with pytest.raises(
        media_source.Unresolvable,
        match="Could not resolve media item: image.non_existing",
    ):
        await media_source.async_resolve_media(
            menuai, "media-source://image/image.non_existing", None
        )
