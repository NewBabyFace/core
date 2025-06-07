"""Test the Panasonic Viera remote entity."""

from unittest.mock import Mock, call

from panasonic_viera import Keys, SOAPError

from menuai.components.panasonic_viera.const import ATTR_UDN, DOMAIN
from menuai.components.remote import (
    ATTR_COMMAND,
    DOMAIN as REMOTE_DOMAIN,
    SERVICE_SEND_COMMAND,
)
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from menuai.core import menuai

from .conftest import MOCK_CONFIG_DATA, MOCK_DEVICE_INFO, MOCK_ENCRYPTION_DATA

from tests.common import MockConfigEntry


async def setup_panasonic_viera(menuai: menuai) -> None:
    """Initialize integration for tests."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DEVICE_INFO[ATTR_UDN],
        data={**MOCK_CONFIG_DATA, **MOCK_ENCRYPTION_DATA, **MOCK_DEVICE_INFO},
    )

    mock_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()


async def test_onoff(menuai: menuai, mock_remote) -> None:
    """Test the on/off service calls."""

    await setup_panasonic_viera(menuai)

    data = {ATTR_ENTITY_ID: "remote.panasonic_viera_tv"}

    # simulate tv off when async_update
    mock_remote.get_mute = Mock(side_effect=SOAPError)

    await menuai.services.async_call(REMOTE_DOMAIN, SERVICE_TURN_OFF, data)
    await menuai.services.async_call(REMOTE_DOMAIN, SERVICE_TURN_ON, data)
    await menuai.async_block_till_done()

    power = getattr(Keys.POWER, "value", Keys.POWER)
    assert mock_remote.send_key.call_args_list == [call(power), call(power)]


async def test_send_command(menuai: menuai, mock_remote) -> None:
    """Test the send_command service call."""

    await setup_panasonic_viera(menuai)

    data = {ATTR_ENTITY_ID: "remote.panasonic_viera_tv", ATTR_COMMAND: "command"}
    await menuai.services.async_call(REMOTE_DOMAIN, SERVICE_SEND_COMMAND, data)
    await menuai.async_block_till_done()

    assert mock_remote.send_key.call_args == call("command")
