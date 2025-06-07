"""The tests for the Graphite component."""

import socket
from unittest import mock
from unittest.mock import patch

import pytest

from menuai.components import graphite
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.setup import async_setup_component


@pytest.fixture(name="mock_gf")
def fixture_mock_gf():
    """Mock Graphite Feeder fixture."""
    with patch("menuai.components.graphite.GraphiteFeeder") as mock_gf:
        yield mock_gf


@pytest.fixture(name="mock_socket")
def fixture_mock_socket():
    """Mock socket fixture."""
    with patch("socket.socket") as mock_socket:
        yield mock_socket


@pytest.fixture(name="mock_time")
def fixture_mock_time():
    """Mock time fixture."""
    with patch("time.time") as mock_time:
        yield mock_time


async def test_setup(menuai: menuai, mock_socket) -> None:
    """Test setup."""
    assert await async_setup_component(menuai, graphite.DOMAIN, {"graphite": {}})
    assert mock_socket.call_count == 1
    assert mock_socket.call_args == mock.call(socket.AF_INET, socket.SOCK_STREAM)


async def test_setup_failure(menuai: menuai, mock_socket) -> None:
    """Test setup fails due to socket error."""
    mock_socket.return_value.connect.side_effect = OSError
    assert not await async_setup_component(menuai, graphite.DOMAIN, {"graphite": {}})

    assert mock_socket.call_count == 1
    assert mock_socket.call_args == mock.call(socket.AF_INET, socket.SOCK_STREAM)
    assert mock_socket.return_value.connect.call_count == 1


async def test_full_config(menuai: menuai, mock_gf, mock_socket) -> None:
    """Test setup with full configuration."""
    config = {"graphite": {"host": "foo", "port": 123, "prefix": "me"}}

    assert await async_setup_component(menuai, graphite.DOMAIN, config)
    assert mock_gf.call_count == 1
    assert mock_gf.call_args == mock.call(menuai, "foo", 123, "tcp", "me")
    assert mock_socket.call_count == 1
    assert mock_socket.call_args == mock.call(socket.AF_INET, socket.SOCK_STREAM)


async def test_full_udp_config(menuai: menuai, mock_gf, mock_socket) -> None:
    """Test setup with full configuration and UDP protocol."""
    config = {
        "graphite": {"host": "foo", "port": 123, "protocol": "udp", "prefix": "me"}
    }

    assert await async_setup_component(menuai, graphite.DOMAIN, config)
    assert mock_gf.call_count == 1
    assert mock_gf.call_args == mock.call(menuai, "foo", 123, "udp", "me")
    assert mock_socket.call_count == 0


async def test_config_port(menuai: menuai, mock_gf, mock_socket) -> None:
    """Test setup with invalid port."""
    config = {"graphite": {"host": "foo", "port": 2003}}

    assert await async_setup_component(menuai, graphite.DOMAIN, config)
    assert mock_gf.called
    assert mock_socket.call_count == 1
    assert mock_socket.call_args == mock.call(socket.AF_INET, socket.SOCK_STREAM)


async def test_start(menuai: menuai, mock_socket, mock_time) -> None:
    """Test the start."""
    mock_time.return_value = 12345
    assert await async_setup_component(menuai, graphite.DOMAIN, {"graphite": {}})
    await menuai.async_block_till_done()
    mock_socket.reset_mock()

    await menuai.async_start()
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", STATE_ON)
    await menuai.async_block_till_done()
    menuai.data[graphite.DOMAIN]._queue.join()

    assert mock_socket.return_value.connect.call_count == 1
    assert mock_socket.return_value.connect.call_args == mock.call(("localhost", 2003))
    assert mock_socket.return_value.sendall.call_count == 1
    assert mock_socket.return_value.sendall.call_args == mock.call(
        b"ha.test.entity.state 1.000000 12345"
    )
    assert mock_socket.return_value.send.call_count == 1
    assert mock_socket.return_value.send.call_args == mock.call(b"\n")
    assert mock_socket.return_value.close.call_count == 1


async def test_shutdown(menuai: menuai, mock_socket, mock_time) -> None:
    """Test the shutdown."""
    mock_time.return_value = 12345
    assert await async_setup_component(menuai, graphite.DOMAIN, {"graphite": {}})
    await menuai.async_block_till_done()
    mock_socket.reset_mock()

    await menuai.async_start()
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", STATE_ON)
    await menuai.async_block_till_done()
    menuai.data[graphite.DOMAIN]._queue.join()

    assert mock_socket.return_value.connect.call_count == 1
    assert mock_socket.return_value.connect.call_args == mock.call(("localhost", 2003))
    assert mock_socket.return_value.sendall.call_count == 1
    assert mock_socket.return_value.sendall.call_args == mock.call(
        b"ha.test.entity.state 1.000000 12345"
    )
    assert mock_socket.return_value.send.call_count == 1
    assert mock_socket.return_value.send.call_args == mock.call(b"\n")
    assert mock_socket.return_value.close.call_count == 1

    mock_socket.reset_mock()

    await menuai.async_stop()
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", STATE_OFF)
    await menuai.async_block_till_done()

    assert mock_socket.return_value.connect.call_count == 0
    assert mock_socket.return_value.sendall.call_count == 0


async def test_report_attributes(menuai: menuai, mock_socket, mock_time) -> None:
    """Test the reporting with attributes."""
    attrs = {"foo": 1, "bar": 2.0, "baz": True, "bat": "NaN"}
    expected = [
        "ha.test.entity.foo 1.000000 12345",
        "ha.test.entity.bar 2.000000 12345",
        "ha.test.entity.baz 1.000000 12345",
        "ha.test.entity.state 1.000000 12345",
    ]

    mock_time.return_value = 12345
    assert await async_setup_component(menuai, graphite.DOMAIN, {"graphite": {}})
    await menuai.async_block_till_done()
    mock_socket.reset_mock()

    await menuai.async_start()
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", STATE_ON, attrs)
    await menuai.async_block_till_done()
    menuai.data[graphite.DOMAIN]._queue.join()

    assert mock_socket.return_value.connect.call_count == 1
    assert mock_socket.return_value.connect.call_args == mock.call(("localhost", 2003))
    assert mock_socket.return_value.sendall.call_count == 1
    assert mock_socket.return_value.sendall.call_args == mock.call(
        "\n".join(expected).encode("utf-8")
    )
    assert mock_socket.return_value.send.call_count == 1
    assert mock_socket.return_value.send.call_args == mock.call(b"\n")
    assert mock_socket.return_value.close.call_count == 1


async def test_report_with_string_state(
    menuai: menuai, mock_socket, mock_time
) -> None:
    """Test the reporting with strings."""
    expected = [
        "ha.test.entity.foo 1.000000 12345",
        "ha.test.entity.state 1.000000 12345",
    ]

    mock_time.return_value = 12345
    assert await async_setup_component(menuai, graphite.DOMAIN, {"graphite": {}})
    await menuai.async_block_till_done()
    mock_socket.reset_mock()

    await menuai.async_start()
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "above_horizon", {"foo": 1.0})
    await menuai.async_block_till_done()
    menuai.data[graphite.DOMAIN]._queue.join()

    assert mock_socket.return_value.connect.call_count == 1
    assert mock_socket.return_value.connect.call_args == mock.call(("localhost", 2003))
    assert mock_socket.return_value.sendall.call_count == 1
    assert mock_socket.return_value.sendall.call_args == mock.call(
        "\n".join(expected).encode("utf-8")
    )
    assert mock_socket.return_value.send.call_count == 1
    assert mock_socket.return_value.send.call_args == mock.call(b"\n")
    assert mock_socket.return_value.close.call_count == 1

    mock_socket.reset_mock()

    menuai.states.async_set("test.entity", "not_float")
    await menuai.async_block_till_done()
    menuai.data[graphite.DOMAIN]._queue.join()

    assert mock_socket.return_value.connect.call_count == 0
    assert mock_socket.return_value.sendall.call_count == 0
    assert mock_socket.return_value.send.call_count == 0
    assert mock_socket.return_value.close.call_count == 0


async def test_report_with_binary_state(
    menuai: menuai, mock_socket, mock_time
) -> None:
    """Test the reporting with binary state."""
    mock_time.return_value = 12345
    assert await async_setup_component(menuai, graphite.DOMAIN, {"graphite": {}})
    await menuai.async_block_till_done()
    mock_socket.reset_mock()

    await menuai.async_start()
    await menuai.async_block_till_done()

    expected = [
        "ha.test.entity.foo 1.000000 12345",
        "ha.test.entity.state 1.000000 12345",
    ]
    menuai.states.async_set("test.entity", STATE_ON, {"foo": 1.0})
    await menuai.async_block_till_done()
    menuai.data[graphite.DOMAIN]._queue.join()

    assert mock_socket.return_value.connect.call_count == 1
    assert mock_socket.return_value.connect.call_args == mock.call(("localhost", 2003))
    assert mock_socket.return_value.sendall.call_count == 1
    assert mock_socket.return_value.sendall.call_args == mock.call(
        "\n".join(expected).encode("utf-8")
    )
    assert mock_socket.return_value.send.call_count == 1
    assert mock_socket.return_value.send.call_args == mock.call(b"\n")
    assert mock_socket.return_value.close.call_count == 1

    mock_socket.reset_mock()

    expected = [
        "ha.test.entity.foo 1.000000 12345",
        "ha.test.entity.state 0.000000 12345",
    ]
    menuai.states.async_set("test.entity", STATE_OFF, {"foo": 1.0})
    await menuai.async_block_till_done()
    menuai.data[graphite.DOMAIN]._queue.join()

    assert mock_socket.return_value.connect.call_count == 1
    assert mock_socket.return_value.connect.call_args == mock.call(("localhost", 2003))
    assert mock_socket.return_value.sendall.call_count == 1
    assert mock_socket.return_value.sendall.call_args == mock.call(
        "\n".join(expected).encode("utf-8")
    )
    assert mock_socket.return_value.send.call_count == 1
    assert mock_socket.return_value.send.call_args == mock.call(b"\n")
    assert mock_socket.return_value.close.call_count == 1


@pytest.mark.parametrize(
    ("error", "log_text"),
    [
        (OSError, "Failed to send data to graphite"),
        (socket.gaierror, "Unable to connect to host"),
        (Exception, "Failed to process STATE_CHANGED event"),
    ],
)
async def test_send_to_graphite_errors(
    menuai: menuai,
    mock_socket,
    mock_time,
    caplog: pytest.LogCaptureFixture,
    error,
    log_text,
) -> None:
    """Test the sending with errors."""
    mock_time.return_value = 12345
    assert await async_setup_component(menuai, graphite.DOMAIN, {"graphite": {}})
    await menuai.async_block_till_done()
    mock_socket.reset_mock()

    await menuai.async_start()
    await menuai.async_block_till_done()

    mock_socket.return_value.connect.side_effect = error

    menuai.states.async_set("test.entity", STATE_ON)
    await menuai.async_block_till_done()
    menuai.data[graphite.DOMAIN]._queue.join()

    assert log_text in caplog.text
