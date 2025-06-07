"""Tests for the Mastodon notify platform."""

from unittest.mock import AsyncMock

from mastodon.Mastodon import MastodonAPIError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.notify import DOMAIN as NOTIFY_DOMAIN
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry


async def test_notify(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_mastodon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sending a message."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.services.has_service(NOTIFY_DOMAIN, "trwnh_mastodon_social")

    await menuai.services.async_call(
        NOTIFY_DOMAIN,
        "trwnh_mastodon_social",
        {
            "message": "test toot",
        },
        blocking=True,
        return_response=False,
    )

    assert mock_mastodon_client.status_post.assert_called_once


async def test_notify_failed(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the notify raising an error."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    mock_mastodon_client.status_post.side_effect = MastodonAPIError

    with pytest.raises(menuaiError, match="Unable to send message"):
        await menuai.services.async_call(
            NOTIFY_DOMAIN,
            "trwnh_mastodon_social",
            {
                "message": "test toot",
            },
            blocking=True,
            return_response=False,
        )
