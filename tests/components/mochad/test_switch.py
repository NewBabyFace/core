"""The tests for the mochad switch platform."""

from unittest import mock

import pytest

from menuai.components import switch
from menuai.components.mochad import switch as mochad
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockEntityPlatform


@pytest.fixture(autouse=True)
def pymochad_mock():
    """Mock pymochad."""
    with (
        mock.patch("menuai.components.mochad.switch.device"),
        mock.patch("menuai.components.mochad.switch.MochadException"),
    ):
        yield


@pytest.fixture
def switch_mock(menuai: menuai) -> mochad.MochadSwitch:
    """Mock switch."""
    controller_mock = mock.MagicMock()
    dev_dict = {"address": "a1", "name": "fake_switch"}
    entity = mochad.MochadSwitch(menuai, controller_mock, dev_dict)
    entity.platform = MockEntityPlatform(menuai)
    return entity


async def test_setup_adds_proper_devices(menuai: menuai) -> None:
    """Test if setup adds devices."""
    good_config = {
        "mochad": {},
        "switch": {
            "platform": "mochad",
            "devices": [{"name": "Switch1", "address": "a1"}],
        },
    }
    assert await async_setup_component(menuai, switch.DOMAIN, good_config)


async def test_name(switch_mock) -> None:
    """Test the name."""
    assert switch_mock.name == "fake_switch"


async def test_turn_on(switch_mock) -> None:
    """Test turn_on."""
    switch_mock.turn_on()
    switch_mock.switch.send_cmd.assert_called_once_with("on")


async def test_turn_off(switch_mock) -> None:
    """Test turn_off."""
    switch_mock.turn_off()
    switch_mock.switch.send_cmd.assert_called_once_with("off")
