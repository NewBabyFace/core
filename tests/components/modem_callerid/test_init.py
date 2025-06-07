"""Test Modem Caller ID integration."""

from unittest.mock import patch

from phone_modem import exceptions

from menuai.components.modem_callerid.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_DEVICE
from menuai.core import menuai

from . import com_port, patch_init_modem

from tests.common import MockConfigEntry


async def test_setup_entry(menuai: menuai) -> None:
    """Test Modem Caller ID entry setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE: com_port().device},
    )
    entry.add_to_menuai(menuai)
    with (
        patch("aioserial.AioSerial", autospec=True),
        patch(
            "menuai.components.modem_callerid.PhoneModem._get_response",
            return_value="OK",
        ),
        patch("phone_modem.PhoneModem._modem_sm"),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED


async def test_async_setup_entry_not_ready(menuai: menuai) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE: com_port().device},
    )
    entry.add_to_menuai(menuai)

    with patch_init_modem() as modemmock:
        modemmock.side_effect = exceptions.SerialError
        await menuai.config_entries.async_setup(entry.entry_id)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert not menuai.data.get(DOMAIN)


async def test_unload_entry(menuai: menuai) -> None:
    """Test unload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE: com_port().device},
    )
    entry.add_to_menuai(menuai)
    with patch_init_modem():
        await menuai.config_entries.async_setup(entry.entry_id)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)
