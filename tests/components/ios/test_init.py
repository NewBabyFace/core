"""Tests for the iOS init file."""

from unittest.mock import patch

import pytest

from menuai.components import ios
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import mock_component


@pytest.fixture(autouse=True)
def mock_load_json():
    """Mock load_json."""
    with patch("menuai.components.ios.load_json_object", return_value={}):
        yield


@pytest.fixture(autouse=True)
def mock_dependencies(menuai: menuai) -> None:
    """Mock dependencies loaded."""
    mock_component(menuai, "zeroconf")
    mock_component(menuai, "device_tracker")


async def test_creating_entry_sets_up_sensor(menuai: menuai) -> None:
    """Test setting up iOS loads the sensor component."""
    with patch(
        "menuai.components.ios.sensor.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        assert await async_setup_component(menuai, ios.DOMAIN, {ios.DOMAIN: {}})
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 1


async def test_configuring_ios_creates_entry(menuai: menuai) -> None:
    """Test that specifying config will create an entry."""
    with patch(
        "menuai.components.ios.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        await async_setup_component(menuai, ios.DOMAIN, {"ios": {"push": {}}})
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 1


async def test_not_configuring_ios_not_creates_entry(menuai: menuai) -> None:
    """Test that no config will not create an entry."""
    with patch(
        "menuai.components.ios.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        await async_setup_component(menuai, ios.DOMAIN, {"foo": "bar"})
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 0
