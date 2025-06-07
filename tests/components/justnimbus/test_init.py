"""Tests for JustNimbus initialization."""

from menuai.components.justnimbus.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .conftest import FIXTURE_OLD_USER_INPUT, FIXTURE_UNIQUE_ID

from tests.common import MockConfigEntry


async def test_config_entry_reauth_at_setup(menuai: menuai) -> None:
    """Test that setting up with old config results in reauth."""
    mock_config = MockConfigEntry(
        domain=DOMAIN, unique_id=FIXTURE_UNIQUE_ID, data=FIXTURE_OLD_USER_INPUT
    )
    mock_config.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config.entry_id)
    await menuai.async_block_till_done()

    assert mock_config.state is ConfigEntryState.SETUP_ERROR
    assert any(mock_config.async_get_active_flows(menuai, {"reauth"}))
