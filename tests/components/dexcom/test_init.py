"""Test the Dexcom config flow."""

from unittest.mock import patch

from pydexcom import AccountError, SessionError

from menuai.components.dexcom.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import CONFIG, init_integration

from tests.common import MockConfigEntry


async def test_setup_entry_account_error(menuai: menuai) -> None:
    """Test entry setup failed due to account error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="test_username",
        unique_id="test_username",
        data=CONFIG,
        options=None,
    )
    with patch(
        "menuai.components.dexcom.Dexcom",
        side_effect=AccountError,
    ):
        entry.add_to_menuai(menuai)
        result = await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert result is False


async def test_setup_entry_session_error(menuai: menuai) -> None:
    """Test entry setup failed due to session error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="test_username",
        unique_id="test_username",
        data=CONFIG,
        options=None,
    )
    with patch(
        "menuai.components.dexcom.Dexcom",
        side_effect=SessionError,
    ):
        entry.add_to_menuai(menuai)
        result = await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert result is False


async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)
