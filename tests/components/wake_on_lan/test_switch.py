"""The tests for the wake on lan switch platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from menuai.components import switch
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from tests.common import async_mock_service


async def test_valid_hostname(
    menuai: menuai, mock_send_magic_packet: AsyncMock
) -> None:
    """Test with valid hostname."""
    assert await async_setup_component(
        menuai,
        switch.DOMAIN,
        {
            "switch": {
                "platform": "wake_on_lan",
                "mac": "00-01-02-03-04-05",
                "host": "validhostname",
            }
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.wake_on_lan")
    assert state.state == STATE_OFF

    with patch("menuai.components.wake_on_lan.switch.sp.call", return_value=0):
        await menuai.services.async_call(
            switch.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.wake_on_lan"},
            blocking=True,
        )

        state = menuai.states.get("switch.wake_on_lan")
        assert state.state == STATE_ON

        await menuai.services.async_call(
            switch.DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "switch.wake_on_lan"},
            blocking=True,
        )

        state = menuai.states.get("switch.wake_on_lan")
        assert state.state == STATE_ON


async def test_broadcast_config_ip_and_port(
    menuai: menuai, mock_send_magic_packet: AsyncMock
) -> None:
    """Test with broadcast address and broadcast port config."""
    mac = "00:01:02:03:04:05"
    broadcast_address = "255.255.255.255"
    port = 999

    assert await async_setup_component(
        menuai,
        switch.DOMAIN,
        {
            "switch": {
                "platform": "wake_on_lan",
                "mac": mac,
                "broadcast_address": broadcast_address,
                "broadcast_port": port,
            }
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.wake_on_lan")
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.wake_on_lan"},
        blocking=True,
    )

    mac = dr.format_mac(mac)
    mock_send_magic_packet.assert_called_with(
        mac, ip_address=broadcast_address, port=port
    )


async def test_broadcast_config_ip(
    menuai: menuai, mock_send_magic_packet: AsyncMock
) -> None:
    """Test with only broadcast address."""

    mac = "00:01:02:03:04:05"
    broadcast_address = "255.255.255.255"

    assert await async_setup_component(
        menuai,
        switch.DOMAIN,
        {
            "switch": {
                "platform": "wake_on_lan",
                "mac": mac,
                "broadcast_address": broadcast_address,
            }
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.wake_on_lan")
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.wake_on_lan"},
        blocking=True,
    )

    mac = dr.format_mac(mac)
    mock_send_magic_packet.assert_called_with(mac, ip_address=broadcast_address)


async def test_broadcast_config_port(
    menuai: menuai, mock_send_magic_packet: AsyncMock
) -> None:
    """Test with only broadcast port config."""

    mac = "00:01:02:03:04:05"
    port = 999

    assert await async_setup_component(
        menuai,
        switch.DOMAIN,
        {"switch": {"platform": "wake_on_lan", "mac": mac, "broadcast_port": port}},
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.wake_on_lan")
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.wake_on_lan"},
        blocking=True,
    )

    mac = dr.format_mac(mac)
    mock_send_magic_packet.assert_called_with(mac, port=port)


async def test_off_script(
    menuai: menuai, mock_send_magic_packet: AsyncMock
) -> None:
    """Test with turn off script."""

    assert await async_setup_component(
        menuai,
        switch.DOMAIN,
        {
            "switch": {
                "platform": "wake_on_lan",
                "mac": "00-01-02-03-04-05",
                "host": "validhostname",
                "turn_off": {"service": "shell_command.turn_off_target"},
            }
        },
    )
    await menuai.async_block_till_done()
    calls = async_mock_service(menuai, "shell_command", "turn_off_target")

    state = menuai.states.get("switch.wake_on_lan")
    assert state.state == STATE_OFF

    with patch("menuai.components.wake_on_lan.switch.sp.call", return_value=0):
        await menuai.services.async_call(
            switch.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.wake_on_lan"},
            blocking=True,
        )

        state = menuai.states.get("switch.wake_on_lan")
        assert state.state == STATE_ON
        assert len(calls) == 0

    with patch("menuai.components.wake_on_lan.switch.sp.call", return_value=1):
        await menuai.services.async_call(
            switch.DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "switch.wake_on_lan"},
            blocking=True,
        )

        state = menuai.states.get("switch.wake_on_lan")
        assert state.state == STATE_OFF
        assert len(calls) == 1


async def test_no_hostname_state(
    menuai: menuai, mock_send_magic_packet: AsyncMock
) -> None:
    """Test that the state updates if we do not pass in a hostname."""

    assert await async_setup_component(
        menuai,
        switch.DOMAIN,
        {
            "switch": {
                "platform": "wake_on_lan",
                "mac": "00-01-02-03-04-05",
            }
        },
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.wake_on_lan")
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.wake_on_lan"},
        blocking=True,
    )

    state = menuai.states.get("switch.wake_on_lan")
    assert state.state == STATE_ON

    await menuai.services.async_call(
        switch.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.wake_on_lan"},
        blocking=True,
    )

    state = menuai.states.get("switch.wake_on_lan")
    assert state.state == STATE_OFF
