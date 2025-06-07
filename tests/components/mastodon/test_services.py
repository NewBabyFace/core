"""Tests for the Mastodon services."""

from unittest.mock import AsyncMock, Mock, patch

from mastodon.Mastodon import MastodonAPIError, MediaAttachment
import pytest

from menuai.components.mastodon.const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_CONTENT_WARNING,
    ATTR_MEDIA,
    ATTR_MEDIA_DESCRIPTION,
    ATTR_STATUS,
    ATTR_VISIBILITY,
    DOMAIN,
)
from menuai.components.mastodon.services import SERVICE_POST
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError

from . import setup_integration

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("payload", "kwargs"),
    [
        (
            {
                ATTR_STATUS: "test toot",
            },
            {
                "status": "test toot",
                "spoiler_text": None,
                "visibility": None,
                "media_ids": None,
                "sensitive": None,
            },
        ),
        (
            {ATTR_STATUS: "test toot", ATTR_VISIBILITY: "private"},
            {
                "status": "test toot",
                "spoiler_text": None,
                "visibility": "private",
                "media_ids": None,
                "sensitive": None,
            },
        ),
        (
            {
                ATTR_STATUS: "test toot",
                ATTR_CONTENT_WARNING: "Spoiler",
                ATTR_VISIBILITY: "private",
            },
            {
                "status": "test toot",
                "spoiler_text": "Spoiler",
                "visibility": "private",
                "media_ids": None,
                "sensitive": None,
            },
        ),
        (
            {
                ATTR_STATUS: "test toot",
                ATTR_CONTENT_WARNING: "Spoiler",
                ATTR_MEDIA: "/image.jpg",
            },
            {
                "status": "test toot",
                "spoiler_text": "Spoiler",
                "visibility": None,
                "media_ids": "1",
                "sensitive": None,
            },
        ),
        (
            {
                ATTR_STATUS: "test toot",
                ATTR_CONTENT_WARNING: "Spoiler",
                ATTR_MEDIA: "/image.jpg",
                ATTR_MEDIA_DESCRIPTION: "A test image",
            },
            {
                "status": "test toot",
                "spoiler_text": "Spoiler",
                "visibility": None,
                "media_ids": "1",
                "sensitive": None,
            },
        ),
    ],
)
async def test_service_post(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    payload: dict[str, str],
    kwargs: dict[str, str | None],
) -> None:
    """Test the post service."""

    await setup_integration(menuai, mock_config_entry)

    with (
        patch.object(menuai.config, "is_allowed_path", return_value=True),
        patch.object(
            mock_mastodon_client, "media_post", return_value=MediaAttachment(id="1")
        ),
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_POST,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            }
            | payload,
            blocking=True,
            return_response=False,
        )

    mock_mastodon_client.status_post.assert_called_with(**kwargs)

    mock_mastodon_client.status_post.reset_mock()


@pytest.mark.parametrize(
    ("payload", "kwargs"),
    [
        (
            {
                ATTR_STATUS: "test toot",
            },
            {"status": "test toot", "spoiler_text": None, "visibility": None},
        ),
        (
            {
                ATTR_STATUS: "test toot",
                ATTR_CONTENT_WARNING: "Spoiler",
                ATTR_MEDIA: "/image.jpg",
            },
            {
                "status": "test toot",
                "spoiler_text": "Spoiler",
                "visibility": None,
                "media_ids": "1",
                "media_description": None,
                "sensitive": None,
            },
        ),
    ],
)
async def test_post_service_failed(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    payload: dict[str, str],
    kwargs: dict[str, str | None],
) -> None:
    """Test the post service raising an error."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    menuai.config.is_allowed_path = Mock(return_value=True)
    mock_mastodon_client.media_post.return_value = MediaAttachment(id="1")

    mock_mastodon_client.status_post.side_effect = MastodonAPIError

    with pytest.raises(menuaiError, match="Unable to send message"):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_POST,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id} | payload,
            blocking=True,
            return_response=False,
        )


async def test_post_media_upload_failed(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the post service raising an error because media upload fails."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    payload = {"status": "test toot", "media": "/fail.jpg"}

    mock_mastodon_client.media_post.side_effect = MastodonAPIError

    with (
        patch.object(menuai.config, "is_allowed_path", return_value=True),
        pytest.raises(menuaiError, match="Unable to upload image /fail.jpg"),
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_POST,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id} | payload,
            blocking=True,
            return_response=False,
        )


async def test_post_path_not_whitelisted(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the post service raising an error because the file path is not whitelisted."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    payload = {"status": "test toot", "media": "/fail.jpg"}

    with pytest.raises(
        menuaiError, match="/fail.jpg is not a whitelisted directory"
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_POST,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id} | payload,
            blocking=True,
            return_response=False,
        )


async def test_service_entry_availability(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the services without valid entry."""
    mock_config_entry.add_to_menuai(menuai)
    mock_config_entry2 = MockConfigEntry(domain=DOMAIN)
    mock_config_entry2.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    payload = {"status": "test toot"}

    with pytest.raises(ServiceValidationError, match="Mock Title is not loaded"):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_POST,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry2.entry_id} | payload,
            blocking=True,
            return_response=False,
        )

    with pytest.raises(
        ServiceValidationError, match='Integration "mastodon" not found in registry'
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_POST,
            {ATTR_CONFIG_ENTRY_ID: "bad-config_id"} | payload,
            blocking=True,
            return_response=False,
        )
