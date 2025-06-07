"""Test the System Bridge integration."""

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import paths

from menuai.components.media_player import BrowseError
from menuai.components.media_source import (
    DOMAIN as MEDIA_SOURCE_DOMAIN,
    URI_SCHEME,
    async_browse_media,
    async_resolve_media,
)
from menuai.components.system_bridge.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
async def setup_component(menuai: menuai) -> None:
    """Set up component."""
    assert await async_setup_component(
        menuai,
        MEDIA_SOURCE_DOMAIN,
        {},
    )


async def test_root(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    init_integration: MockConfigEntry,
) -> None:
    """Test root media browsing."""
    browse_media_root = await async_browse_media(
        menuai,
        f"{URI_SCHEME}{DOMAIN}",
    )

    assert browse_media_root.as_dict() == snapshot(
        name=f"{DOMAIN}_media_source_root",
        exclude=paths("children", "media_content_id"),
    )


async def test_entry(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    init_integration: MockConfigEntry,
) -> None:
    """Test browsing entry."""
    browse_media_entry = await async_browse_media(
        menuai,
        f"{URI_SCHEME}{DOMAIN}/{init_integration.entry_id}",
    )

    assert browse_media_entry.as_dict() == snapshot(
        name=f"{DOMAIN}_media_source_entry",
        exclude=paths("children", "media_content_id"),
    )


async def test_directory(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    init_integration: MockConfigEntry,
) -> None:
    """Test browsing directory."""
    browse_media_directory = await async_browse_media(
        menuai,
        f"{URI_SCHEME}{DOMAIN}/{init_integration.entry_id}~~documents",
    )

    assert browse_media_directory.as_dict() == snapshot(
        name=f"{DOMAIN}_media_source_directory",
        exclude=paths("children", "media_content_id"),
    )


async def test_subdirectory(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    init_integration: MockConfigEntry,
) -> None:
    """Test browsing directory."""
    browse_media_directory = await async_browse_media(
        menuai,
        f"{URI_SCHEME}{DOMAIN}/{init_integration.entry_id}~~documents/testsubdirectory",
    )

    assert browse_media_directory.as_dict() == snapshot(
        name=f"{DOMAIN}_media_source_subdirectory",
        exclude=paths("children", "media_content_id"),
    )


async def test_file(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    init_integration: MockConfigEntry,
) -> None:
    """Test browsing file."""
    resolve_media_file = await async_resolve_media(
        menuai,
        f"{URI_SCHEME}{DOMAIN}/{init_integration.entry_id}~~documents/testfile.txt~~text/plain",
        None,
    )

    assert resolve_media_file == snapshot(
        name=f"{DOMAIN}_media_source_file_text",
    )

    resolve_media_file = await async_resolve_media(
        menuai,
        f"{URI_SCHEME}{DOMAIN}/{init_integration.entry_id}~~documents/testimage.jpg~~image/jpeg",
        None,
    )

    assert resolve_media_file == snapshot(
        name=f"{DOMAIN}_media_source_file_image",
    )


async def test_bad_entry(
    menuai: menuai,
    init_integration: MockConfigEntry,
) -> None:
    """Test invalid entry raises BrowseError."""
    with pytest.raises(BrowseError):
        await async_browse_media(
            menuai,
            f"{URI_SCHEME}{DOMAIN}/badentryid",
        )

    with pytest.raises(BrowseError):
        await async_browse_media(
            menuai,
            f"{URI_SCHEME}{DOMAIN}/badentryid~~baddirectory",
        )

    with pytest.raises(ValueError):
        await async_resolve_media(
            menuai,
            f"{URI_SCHEME}{DOMAIN}/badentryid~~baddirectory/badfile.txt~~text/plain",
            None,
        )
