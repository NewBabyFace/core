"""Tests for the light module."""

from unittest.mock import MagicMock

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.light import ATTR_BRIGHTNESS, DOMAIN as LIGHT_DOMAIN
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


async def test_light_setup_with_device(
    menuai: menuai,
    pydeako_deako_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test light platform setup with device returned."""
    mock_config_entry.add_to_menuai(menuai)

    pydeako_deako_mock.return_value.get_devices.return_value = {
        "some_device": {},
    }
    pydeako_deako_mock.return_value.get_name.return_value = "some device"

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_light_initial_props(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    pydeako_deako_mock: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test on/off light is setup with accurate initial properties."""
    mock_config_entry.add_to_menuai(menuai)

    pydeako_deako_mock.return_value.get_devices.return_value = {
        "uuid": {
            "name": "kitchen",
        }
    }
    pydeako_deako_mock.return_value.get_name.return_value = "kitchen"
    pydeako_deako_mock.return_value.get_state.return_value = {
        "power": False,
    }
    pydeako_deako_mock.return_value.is_dimmable.return_value = False

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_dimmable_light_props(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    pydeako_deako_mock: MagicMock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test dimmable on/off light is setup with accurate initial properties."""
    mock_config_entry.add_to_menuai(menuai)

    pydeako_deako_mock.return_value.get_devices.return_value = {
        "uuid": {
            "name": "kitchen",
        }
    }
    pydeako_deako_mock.return_value.get_name.return_value = "kitchen"
    pydeako_deako_mock.return_value.get_state.return_value = {
        "power": True,
        "dim": 50,
    }
    pydeako_deako_mock.return_value.is_dimmable.return_value = True

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_light_power_change_on(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    pydeako_deako_mock: MagicMock,
) -> None:
    """Test turing on a deako device."""
    mock_config_entry.add_to_menuai(menuai)

    pydeako_deako_mock.return_value.get_devices.return_value = {
        "uuid": {
            "name": "kitchen",
        }
    }
    pydeako_deako_mock.return_value.get_name.return_value = "kitchen"

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "light.kitchen"},
        blocking=True,
    )

    pydeako_deako_mock.return_value.control_device.assert_called_once_with(
        "uuid", True, None
    )


async def test_light_power_change_off(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    pydeako_deako_mock: MagicMock,
) -> None:
    """Test turing off a deako device."""
    mock_config_entry.add_to_menuai(menuai)

    pydeako_deako_mock.return_value.get_devices.return_value = {
        "uuid": {
            "name": "kitchen",
        }
    }
    pydeako_deako_mock.return_value.get_name.return_value = "kitchen"

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "light.kitchen"},
        blocking=True,
    )

    pydeako_deako_mock.return_value.control_device.assert_called_once_with(
        "uuid", False, None
    )


@pytest.mark.parametrize(
    ("dim_input", "expected_dim_value"),
    [
        (3, 1),
        (255, 100),
        (127, 50),
    ],
)
async def test_light_brightness_change(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    pydeako_deako_mock: MagicMock,
    dim_input: int,
    expected_dim_value: int,
) -> None:
    """Test turing on a deako device."""
    mock_config_entry.add_to_menuai(menuai)

    pydeako_deako_mock.return_value.get_devices.return_value = {
        "uuid": {
            "name": "kitchen",
        }
    }
    pydeako_deako_mock.return_value.get_name.return_value = "kitchen"

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "light.kitchen",
            ATTR_BRIGHTNESS: dim_input,
        },
        blocking=True,
    )

    pydeako_deako_mock.return_value.control_device.assert_called_once_with(
        "uuid", True, expected_dim_value
    )
