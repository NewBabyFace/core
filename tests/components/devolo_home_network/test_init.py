"""Test the devolo Home Network integration setup."""

from unittest.mock import patch

from devolo_plc_api.exceptions.device import DeviceNotFound
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR
from menuai.components.button import DOMAIN as BUTTON
from menuai.components.device_tracker import DOMAIN as DEVICE_TRACKER
from menuai.components.devolo_home_network.const import DOMAIN
from menuai.components.image import DOMAIN as IMAGE
from menuai.components.sensor import DOMAIN as SENSOR
from menuai.components.switch import DOMAIN as SWITCH
from menuai.components.update import DOMAIN as UPDATE
from menuai.config_entries import ConfigEntryState
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.helpers.entity_platform import async_get_platforms

from . import configure_integration
from .const import IP
from .mock import MockDevice


@pytest.mark.parametrize(
    "device", ["mock_device", "mock_repeater_device", "mock_ipv6_device"]
)
async def test_setup_entry(
    menuai: menuai,
    device: str,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
    request: pytest.FixtureRequest,
) -> None:
    """Test setup entry."""
    mock_device: MockDevice = request.getfixturevalue(device)
    entry = configure_integration(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    device_info = device_registry.async_get_device(
        {(DOMAIN, mock_device.serial_number)}
    )
    assert device_info == snapshot


async def test_setup_device_not_found(menuai: menuai) -> None:
    """Test setup entry."""
    entry = configure_integration(menuai)
    with patch(
        "menuai.components.devolo_home_network.Device.async_connect",
        side_effect=DeviceNotFound(IP),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("mock_device")
async def test_unload_entry(menuai: menuai) -> None:
    """Test unload entry."""
    entry = configure_integration(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    await menuai.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_menuai_stop(menuai: menuai, mock_device: MockDevice) -> None:
    """Test menuai stop event."""
    entry = configure_integration(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()
    mock_device.async_disconnect.assert_called_once()


@pytest.mark.parametrize(
    ("device", "expected_platforms"),
    [
        (
            "mock_device",
            (BINARY_SENSOR, BUTTON, DEVICE_TRACKER, IMAGE, SENSOR, SWITCH, UPDATE),
        ),
        (
            "mock_repeater_device",
            (BUTTON, DEVICE_TRACKER, IMAGE, SENSOR, SWITCH, UPDATE),
        ),
        ("mock_nonwifi_device", (BINARY_SENSOR, BUTTON, SENSOR, SWITCH, UPDATE)),
    ],
)
async def test_platforms(
    menuai: menuai,
    device: str,
    expected_platforms: set[str],
    request: pytest.FixtureRequest,
) -> None:
    """Test platform assembly."""
    request.getfixturevalue(device)
    entry = configure_integration(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    platforms = [platform.domain for platform in async_get_platforms(menuai, DOMAIN)]
    assert len(platforms) == len(expected_platforms)
    assert all(platform in platforms for platform in expected_platforms)
