"""The tests for the pilight component."""

from datetime import timedelta
import logging
import socket
from unittest.mock import patch

import pytest
from voluptuous import MultipleInvalid

from menuai.components import pilight
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import (
    assert_setup_component,
    async_capture_events,
    async_fire_time_changed,
)

_LOGGER = logging.getLogger(__name__)


class PilightDaemonSim:
    """Class to fake the interface of the pilight python package.

    Is used in an asyncio loop, thus the mock cannot be accessed to
    determine if methods where called?!
    This is solved here in a hackish way by printing errors
    that can be checked using logging.error mocks.
    """

    callback = None
    called = None

    test_message = {
        "protocol": "kaku_switch",
        "uuid": "1-2-3-4",
        "message": {"id": 0, "unit": 0, "off": 1},
    }

    def __init__(self, host, port) -> None:
        """Init pilight client, ignore parameters."""

    def send_code(self, call):
        """Handle pilight.send service callback."""
        _LOGGER.error("PilightDaemonSim payload: %s", call)

    def start(self):
        """Handle menuai.start callback.

        Also sends one test message after start up
        """
        _LOGGER.error("PilightDaemonSim start")
        # Fake one code receive after daemon started
        if not self.called:
            self.callback(self.test_message)
            self.called = True

    def stop(self):
        """Handle menuai.stop callback."""
        _LOGGER.error("PilightDaemonSim stop")

    def set_callback(self, function):
        """Handle pilight.pilight_received event callback."""
        self.callback = function
        _LOGGER.error("PilightDaemonSim callback: %s", function)


@patch("menuai.components.pilight._LOGGER.error")
async def test_connection_failed_error(mock_error, menuai: menuai) -> None:
    """Try to connect at 127.0.0.1:5001 with socket error."""
    with (
        assert_setup_component(4),
        patch("pilight.pilight.Client", side_effect=socket.error) as mock_client,
    ):
        assert not await async_setup_component(
            menuai, pilight.DOMAIN, {pilight.DOMAIN: {}}
        )
        mock_client.assert_called_once_with(
            host=pilight.DEFAULT_HOST, port=pilight.DEFAULT_PORT
        )
        assert mock_error.call_count == 1


@patch("menuai.components.pilight._LOGGER.error")
async def test_connection_timeout_error(mock_error, menuai: menuai) -> None:
    """Try to connect at 127.0.0.1:5001 with socket timeout."""
    with (
        assert_setup_component(4),
        patch("pilight.pilight.Client", side_effect=socket.timeout) as mock_client,
    ):
        assert not await async_setup_component(
            menuai, pilight.DOMAIN, {pilight.DOMAIN: {}}
        )
        mock_client.assert_called_once_with(
            host=pilight.DEFAULT_HOST, port=pilight.DEFAULT_PORT
        )
        assert mock_error.call_count == 1


@patch("pilight.pilight.Client", PilightDaemonSim)
async def test_send_code_no_protocol(menuai: menuai) -> None:
    """Try to send data without protocol information, should give error."""
    with assert_setup_component(4):
        assert await async_setup_component(menuai, pilight.DOMAIN, {pilight.DOMAIN: {}})

        # Call without protocol info, should raise an error
        with pytest.raises(MultipleInvalid) as excinfo:
            await menuai.services.async_call(
                pilight.DOMAIN,
                pilight.SERVICE_NAME,
                service_data={"noprotocol": "test", "value": 42},
                blocking=True,
            )
        assert "required key not provided @ data['protocol']" in str(excinfo.value)


@patch("menuai.components.pilight._LOGGER.error")
@patch("menuai.components.pilight._LOGGER", _LOGGER)
@patch("pilight.pilight.Client", PilightDaemonSim)
async def test_send_code(mock_pilight_error, menuai: menuai) -> None:
    """Try to send proper data."""
    with assert_setup_component(4):
        assert await async_setup_component(menuai, pilight.DOMAIN, {pilight.DOMAIN: {}})

        # Call with protocol info, should not give error
        service_data = {"protocol": "test", "value": 42}
        await menuai.services.async_call(
            pilight.DOMAIN,
            pilight.SERVICE_NAME,
            service_data=service_data,
            blocking=True,
        )
        await menuai.async_block_till_done()
        error_log_call = mock_pilight_error.call_args_list[-1]
        service_data["protocol"] = [service_data["protocol"]]
        assert str(service_data) in str(error_log_call)


@patch("pilight.pilight.Client", PilightDaemonSim)
@patch("menuai.components.pilight._LOGGER.error")
async def test_send_code_fail(mock_pilight_error, menuai: menuai) -> None:
    """Check IOError exception error message."""
    with (
        assert_setup_component(4),
        patch("pilight.pilight.Client.send_code", side_effect=IOError),
    ):
        assert await async_setup_component(menuai, pilight.DOMAIN, {pilight.DOMAIN: {}})

        # Call with protocol info, should not give error
        service_data = {"protocol": "test", "value": 42}
        await menuai.services.async_call(
            pilight.DOMAIN,
            pilight.SERVICE_NAME,
            service_data=service_data,
            blocking=True,
        )
        await menuai.async_block_till_done()
        error_log_call = mock_pilight_error.call_args_list[-1]
        assert "Pilight send failed" in str(error_log_call)


@patch("menuai.components.pilight._LOGGER.error")
@patch("menuai.components.pilight._LOGGER", _LOGGER)
@patch("pilight.pilight.Client", PilightDaemonSim)
async def test_send_code_delay(mock_pilight_error, menuai: menuai) -> None:
    """Try to send proper data with delay afterwards."""
    with assert_setup_component(4):
        assert await async_setup_component(
            menuai,
            pilight.DOMAIN,
            {pilight.DOMAIN: {pilight.CONF_SEND_DELAY: 5.0}},
        )

        # Call with protocol info, should not give error
        service_data1 = {"protocol": "test11", "value": 42}
        service_data2 = {"protocol": "test22", "value": 42}
        await menuai.services.async_call(
            pilight.DOMAIN,
            pilight.SERVICE_NAME,
            service_data=service_data1,
            blocking=True,
        )
        await menuai.services.async_call(
            pilight.DOMAIN,
            pilight.SERVICE_NAME,
            service_data=service_data2,
            blocking=True,
        )
        service_data1["protocol"] = [service_data1["protocol"]]
        service_data2["protocol"] = [service_data2["protocol"]]

        async_fire_time_changed(menuai, dt_util.utcnow())
        await menuai.async_block_till_done()
        error_log_call = mock_pilight_error.call_args_list[-1]
        assert str(service_data1) in str(error_log_call)

        new_time = dt_util.utcnow() + timedelta(seconds=5)
        async_fire_time_changed(menuai, new_time)
        await menuai.async_block_till_done()
        error_log_call = mock_pilight_error.call_args_list[-1]
        assert str(service_data2) in str(error_log_call)


@patch("menuai.components.pilight._LOGGER.error")
@patch("menuai.components.pilight._LOGGER", _LOGGER)
@patch("pilight.pilight.Client", PilightDaemonSim)
async def test_start_stop(mock_pilight_error, menuai: menuai) -> None:
    """Check correct startup and stop of pilight daemon."""
    with assert_setup_component(4):
        assert await async_setup_component(menuai, pilight.DOMAIN, {pilight.DOMAIN: {}})

        # Test startup
        await menuai.async_start()
        await menuai.async_block_till_done()

        error_log_call = mock_pilight_error.call_args_list[-2]
        assert "PilightDaemonSim callback" in str(error_log_call)
        error_log_call = mock_pilight_error.call_args_list[-1]
        assert "PilightDaemonSim start" in str(error_log_call)

        # Test stop
        with patch.object(menuai.loop, "stop"):
            await menuai.async_stop()
        error_log_call = mock_pilight_error.call_args_list[-1]
        assert "PilightDaemonSim stop" in str(error_log_call)


@patch("pilight.pilight.Client", PilightDaemonSim)
async def test_receive_code(menuai: menuai) -> None:
    """Check if code receiving via pilight daemon works."""
    events = async_capture_events(menuai, pilight.EVENT)
    with assert_setup_component(4):
        assert await async_setup_component(menuai, pilight.DOMAIN, {pilight.DOMAIN: {}})

        # Test startup
        await menuai.async_start()
        await menuai.async_block_till_done()

        expected_message = dict(
            {
                "protocol": PilightDaemonSim.test_message["protocol"],
                "uuid": PilightDaemonSim.test_message["uuid"],
            },
            **PilightDaemonSim.test_message["message"],
        )
        assert events[0].data == expected_message


@patch("pilight.pilight.Client", PilightDaemonSim)
async def test_whitelist_exact_match(menuai: menuai) -> None:
    """Check whitelist filter with matched data."""
    events = async_capture_events(menuai, pilight.EVENT)
    with assert_setup_component(4):
        whitelist = {
            "protocol": [PilightDaemonSim.test_message["protocol"]],
            "uuid": [PilightDaemonSim.test_message["uuid"]],
            "id": [PilightDaemonSim.test_message["message"]["id"]],
            "unit": [PilightDaemonSim.test_message["message"]["unit"]],
        }
        assert await async_setup_component(
            menuai, pilight.DOMAIN, {pilight.DOMAIN: {"whitelist": whitelist}}
        )

        await menuai.async_start()
        await menuai.async_block_till_done()

        expected_message = dict(
            {
                "protocol": PilightDaemonSim.test_message["protocol"],
                "uuid": PilightDaemonSim.test_message["uuid"],
            },
            **PilightDaemonSim.test_message["message"],
        )
        # Check if all message parts are put on event bus
        assert events[0].data == expected_message


@patch("pilight.pilight.Client", PilightDaemonSim)
async def test_whitelist_partial_match(menuai: menuai) -> None:
    """Check whitelist filter with partially matched data, should work."""
    events = async_capture_events(menuai, pilight.EVENT)
    with assert_setup_component(4):
        whitelist = {
            "protocol": [PilightDaemonSim.test_message["protocol"]],
            "id": [PilightDaemonSim.test_message["message"]["id"]],
        }
        assert await async_setup_component(
            menuai, pilight.DOMAIN, {pilight.DOMAIN: {"whitelist": whitelist}}
        )

        await menuai.async_start()
        await menuai.async_block_till_done()

        expected_message = dict(
            {
                "protocol": PilightDaemonSim.test_message["protocol"],
                "uuid": PilightDaemonSim.test_message["uuid"],
            },
            **PilightDaemonSim.test_message["message"],
        )
        # Check if all message parts are put on event bus
        assert events[0].data == expected_message


@patch("pilight.pilight.Client", PilightDaemonSim)
async def test_whitelist_or_match(menuai: menuai) -> None:
    """Check whitelist filter with several subsection, should work."""
    events = async_capture_events(menuai, pilight.EVENT)

    with assert_setup_component(4):
        whitelist = {
            "protocol": [
                PilightDaemonSim.test_message["protocol"],
                "other_protocol",
            ],
            "id": [PilightDaemonSim.test_message["message"]["id"]],
        }
        assert await async_setup_component(
            menuai, pilight.DOMAIN, {pilight.DOMAIN: {"whitelist": whitelist}}
        )

        await menuai.async_start()
        await menuai.async_block_till_done()

        expected_message = dict(
            {
                "protocol": PilightDaemonSim.test_message["protocol"],
                "uuid": PilightDaemonSim.test_message["uuid"],
            },
            **PilightDaemonSim.test_message["message"],
        )
        # Check if all message parts are put on event bus
        assert events[0].data == expected_message


@patch("pilight.pilight.Client", PilightDaemonSim)
async def test_whitelist_no_match(menuai: menuai) -> None:
    """Check whitelist filter with unmatched data, should not work."""
    events = async_capture_events(menuai, pilight.EVENT)

    with assert_setup_component(4):
        whitelist = {
            "protocol": ["wrong_protocol"],
            "id": [PilightDaemonSim.test_message["message"]["id"]],
        }
        assert await async_setup_component(
            menuai, pilight.DOMAIN, {pilight.DOMAIN: {"whitelist": whitelist}}
        )

        await menuai.async_start()
        await menuai.async_block_till_done()

        assert len(events) == 0


async def test_call_rate_delay_throttle_enabled(menuai: menuai) -> None:
    """Test that throttling actually work."""
    runs = []
    delay = 5.0

    limit = pilight.CallRateDelayThrottle(menuai, delay)
    # pylint: disable-next=unnecessary-lambda
    action = limit.limited(lambda x: runs.append(x))

    for i in range(3):
        await menuai.async_add_executor_job(action, i)

    await menuai.async_block_till_done()
    assert runs == [0]

    exp = []
    now = dt_util.utcnow()
    for i in range(3):
        exp.append(i)
        shifted_time = now + (timedelta(seconds=delay + 0.1) * i)
        async_fire_time_changed(menuai, shifted_time)
        await menuai.async_block_till_done()
        assert runs == exp


def test_call_rate_delay_throttle_disabled(menuai: menuai) -> None:
    """Test that the limiter is a noop if no delay set."""
    runs = []

    limit = pilight.CallRateDelayThrottle(menuai, 0.0)
    # pylint: disable-next=unnecessary-lambda
    action = limit.limited(lambda x: runs.append(x))

    for i in range(3):
        action(i)

    assert runs == [0, 1, 2]
