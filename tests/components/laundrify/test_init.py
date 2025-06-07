"""Test the laundrify init file."""

from laundrify_aio import exceptions

from menuai.components.laundrify.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_ACCESS_TOKEN
from menuai.core import menuai

from .const import VALID_ACCESS_TOKEN

from tests.common import MockConfigEntry


async def test_setup_entry_api_unauthorized(
    menuai: menuai,
    laundrify_api_mock,
    laundrify_config_entry: MockConfigEntry,
) -> None:
    """Test that ConfigEntryAuthFailed is thrown when authentication fails."""
    laundrify_api_mock.validate_token.side_effect = exceptions.UnauthorizedException
    await menuai.config_entries.async_reload(laundrify_config_entry.entry_id)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert laundrify_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert not menuai.data.get(DOMAIN)


async def test_setup_entry_api_cannot_connect(
    menuai: menuai,
    laundrify_api_mock,
    laundrify_config_entry: MockConfigEntry,
) -> None:
    """Test that ApiConnectionException is thrown when connection fails."""
    laundrify_api_mock.validate_token.side_effect = exceptions.ApiConnectionException
    await menuai.config_entries.async_reload(laundrify_config_entry.entry_id)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert laundrify_config_entry.state is ConfigEntryState.SETUP_RETRY
    assert not menuai.data.get(DOMAIN)


async def test_setup_entry_successful(
    menuai: menuai, laundrify_config_entry: MockConfigEntry
) -> None:
    """Test entry can be setup successfully."""
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert laundrify_config_entry.state is ConfigEntryState.LOADED


async def test_setup_entry_unload(
    menuai: menuai, laundrify_config_entry: MockConfigEntry
) -> None:
    """Test unloading the laundrify entry."""
    await menuai.config_entries.async_unload(laundrify_config_entry.entry_id)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert laundrify_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_migrate_entry_minor_version_1_2(menuai: menuai) -> None:
    """Test migrating a 1.1 config entry to 1.2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ACCESS_TOKEN: VALID_ACCESS_TOKEN},
        version=1,
        minor_version=1,
        unique_id=123456,
    )
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.version == 1
    assert entry.minor_version == 2
    assert entry.unique_id == "123456"
