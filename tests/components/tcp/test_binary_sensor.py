"""The tests for the TCP binary sensor platform."""

from datetime import timedelta
from unittest.mock import call, patch

import pytest

from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from . import test_sensor as test_tcp

from tests.common import assert_setup_component, async_fire_time_changed

BINARY_SENSOR_CONFIG = test_tcp.TEST_CONFIG["sensor"]
TEST_CONFIG = {"binary_sensor": BINARY_SENSOR_CONFIG}
TEST_ENTITY = "binary_sensor.test_name"


@pytest.fixture(name="mock_socket")
def mock_socket_fixture():
    """Mock the socket."""
    with (
        patch("menuai.components.tcp.entity.socket.socket") as mock_socket,
        patch(
            "menuai.components.tcp.entity.select.select",
            return_value=(True, False, False),
        ),
    ):
        # yield the return value of the socket context manager
        yield mock_socket.return_value.__enter__.return_value


@pytest.fixture
def now():
    """Return datetime UTC now."""
    return utcnow()


async def test_setup_platform_valid_config(menuai: menuai, mock_socket) -> None:
    """Check a valid configuration."""
    with assert_setup_component(1, "binary_sensor"):
        assert await async_setup_component(menuai, "binary_sensor", TEST_CONFIG)
        await menuai.async_block_till_done()


async def test_setup_platform_invalid_config(menuai: menuai, mock_socket) -> None:
    """Check the invalid configuration."""
    with assert_setup_component(0):
        assert await async_setup_component(
            menuai,
            "binary_sensor",
            {"binary_sensor": {"platform": "tcp", "porrt": 1234}},
        )
        await menuai.async_block_till_done()


async def test_state(menuai: menuai, mock_socket, now) -> None:
    """Check the state and update of the binary sensor."""
    mock_socket.recv.return_value = b"off"
    assert await async_setup_component(menuai, "binary_sensor", TEST_CONFIG)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY)

    assert state
    assert state.state == STATE_OFF
    assert mock_socket.connect.called
    assert mock_socket.connect.call_args == call(
        (BINARY_SENSOR_CONFIG["host"], BINARY_SENSOR_CONFIG["port"])
    )
    assert mock_socket.send.called
    assert mock_socket.send.call_args == call(BINARY_SENSOR_CONFIG["payload"].encode())
    assert mock_socket.recv.called
    assert mock_socket.recv.call_args == call(BINARY_SENSOR_CONFIG["buffer_size"])

    mock_socket.recv.return_value = b"on"

    async_fire_time_changed(menuai, now + timedelta(seconds=45))
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(TEST_ENTITY)

    assert state
    assert state.state == STATE_ON
