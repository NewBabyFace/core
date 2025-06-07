"""Tests for the Mastodon integration."""

from unittest.mock import AsyncMock

from mastodon.Mastodon import MastodonError
from syrupy.assertion import SnapshotAssertion

from menuai.components.mastodon.config_flow import MastodonConfigFlow
from menuai.components.mastodon.const import CONF_BASE_URL, DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_ACCESS_TOKEN, CONF_CLIENT_ID, CONF_CLIENT_SECRET
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import setup_integration

from tests.common import MockConfigEntry


async def test_device_info(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_mastodon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test device registry integration."""
    await setup_integration(menuai, mock_config_entry)
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, mock_config_entry.unique_id)}
    )
    assert device_entry is not None
    assert device_entry == snapshot


async def test_initialization_failure(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test initialization failure."""
    mock_mastodon_client.instance.side_effect = MastodonError

    await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_migrate(
    menuai: menuai,
    mock_mastodon_client: AsyncMock,
) -> None:
    """Test migration."""
    # Setup the config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_BASE_URL: "https://mastodon.social",
            CONF_CLIENT_ID: "client_id",
            CONF_CLIENT_SECRET: "client_secret",
            CONF_ACCESS_TOKEN: "access_token",
        },
        title="@trwnh@mastodon.social",
        unique_id="client_id",
        version=1,
        minor_version=1,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Check migration was successful
    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.data == {
        CONF_BASE_URL: "https://mastodon.social",
        CONF_CLIENT_ID: "client_id",
        CONF_CLIENT_SECRET: "client_secret",
        CONF_ACCESS_TOKEN: "access_token",
    }
    assert config_entry.version == MastodonConfigFlow.VERSION
    assert config_entry.minor_version == MastodonConfigFlow.MINOR_VERSION
    assert config_entry.unique_id == "trwnh_mastodon_social"
