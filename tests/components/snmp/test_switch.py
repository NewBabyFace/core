"""SNMP switch tests."""

from unittest.mock import patch

from pysnmp.proto.rfc1902 import Integer32
import pytest

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from menuai.core import menuai
from menuai.setup import async_setup_component

config = {
    SWITCH_DOMAIN: {
        "platform": "snmp",
        "host": "192.168.1.32",
        # ippower-mib::ippoweroutlet1.0
        "baseoid": "1.3.6.1.4.1.38107.1.3.1.0",
        "payload_on": 1,
        "payload_off": 0,
    },
}


async def test_snmp_integer_switch_off(menuai: menuai) -> None:
    """Test snmp switch returning int 0 for off."""

    mock_data = Integer32(0)
    with patch(
        "menuai.components.snmp.switch.getCmd",
        return_value=(None, None, None, [[mock_data]]),
    ):
        assert await async_setup_component(menuai, SWITCH_DOMAIN, config)
        await menuai.async_block_till_done()
        state = menuai.states.get("switch.snmp")
        assert state.state == STATE_OFF


async def test_snmp_integer_switch_on(menuai: menuai) -> None:
    """Test snmp switch returning int 1 for on."""

    mock_data = Integer32(1)
    with patch(
        "menuai.components.snmp.switch.getCmd",
        return_value=(None, None, None, [[mock_data]]),
    ):
        assert await async_setup_component(menuai, SWITCH_DOMAIN, config)
        await menuai.async_block_till_done()
        state = menuai.states.get("switch.snmp")
        assert state.state == STATE_ON


async def test_snmp_integer_switch_unknown(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test snmp switch returning int 3 (not a configured payload) for unknown."""

    mock_data = Integer32(3)
    with patch(
        "menuai.components.snmp.switch.getCmd",
        return_value=(None, None, None, [[mock_data]]),
    ):
        assert await async_setup_component(menuai, SWITCH_DOMAIN, config)
        await menuai.async_block_till_done()
        state = menuai.states.get("switch.snmp")
        assert state.state == STATE_UNKNOWN
        assert "Invalid payload '3' received for entity" in caplog.text
