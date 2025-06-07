"""Test the One-Time Password (OTP) init."""

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_entry_setup_unload(
    menuai: menuai, otp_config_entry: MockConfigEntry
) -> None:
    """Test integration setup and unload."""

    otp_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(otp_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert otp_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(otp_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert otp_config_entry.state is ConfigEntryState.NOT_LOADED
