"""Test the myStrom init."""

from unittest.mock import AsyncMock, PropertyMock, patch

from pymystrom.exceptions import MyStromConnectionError
import pytest

from menuai.components.mystrom.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import (
    MyStromBulbMock,
    MyStromSwitchMock,
    get_default_bulb_state,
    get_default_device_response,
    get_default_switch_state,
)
from .conftest import DEVICE_MAC

from tests.common import MockConfigEntry


async def init_integration(
    menuai: menuai,
    config_entry: MockConfigEntry,
    device_type: int,
) -> None:
    """Initialize integration for testing."""
    with (
        patch(
            "pymystrom.get_device_info",
            side_effect=AsyncMock(
                return_value=get_default_device_response(device_type)
            ),
        ),
        patch(
            "menuai.components.mystrom._get_mystrom_bulb",
            return_value=MyStromBulbMock("6001940376EB", get_default_bulb_state()),
        ),
        patch(
            "menuai.components.mystrom._get_mystrom_switch",
            return_value=MyStromSwitchMock(get_default_switch_state()),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()


async def test_init_switch_and_unload(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test the initialization of a myStrom switch."""
    await init_integration(menuai, config_entry, 106)
    state = menuai.states.get("switch.mystrom_device")
    assert state is not None
    assert config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


@pytest.mark.parametrize(
    ("device_type", "platform", "entry_state", "entity_state_none"),
    [
        (None, "switch", ConfigEntryState.LOADED, False),
        (102, "light", ConfigEntryState.LOADED, False),
        (103, "button", ConfigEntryState.SETUP_ERROR, True),
        (104, "button", ConfigEntryState.SETUP_ERROR, True),
        (105, "light", ConfigEntryState.LOADED, False),
        (106, "switch", ConfigEntryState.LOADED, False),
        (107, "switch", ConfigEntryState.LOADED, False),
        (110, "sensor", ConfigEntryState.SETUP_ERROR, True),
        (113, "switch", ConfigEntryState.SETUP_ERROR, True),
        (118, "button", ConfigEntryState.SETUP_ERROR, True),
        (120, "switch", ConfigEntryState.LOADED, False),
    ],
)
async def test_init_bulb(
    menuai: menuai,
    config_entry: MockConfigEntry,
    device_type: int,
    platform: str,
    entry_state: ConfigEntryState,
    entity_state_none: bool,
) -> None:
    """Test the initialization of a myStrom bulb."""
    await init_integration(menuai, config_entry, device_type)
    state = menuai.states.get(f"{platform}.mystrom_device")
    assert (state is None) == entity_state_none
    assert config_entry.state is entry_state


async def test_init_of_unknown_bulb(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test the initialization of a unknown myStrom bulb."""
    with (
        patch(
            "pymystrom.get_device_info",
            side_effect=AsyncMock(return_value={"type": 102, "mac": DEVICE_MAC}),
        ),
        patch("pymystrom.bulb.MyStromBulb.get_state", return_value={}),
        patch("pymystrom.bulb.MyStromBulb.bulb_type", "new_type"),
        patch(
            "pymystrom.bulb.MyStromBulb.mac",
            new_callable=PropertyMock,
            return_value=DEVICE_MAC,
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_init_of_unknown_device(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test the initialization of a unsupported myStrom device."""
    with patch(
        "pymystrom.get_device_info",
        side_effect=AsyncMock(return_value={"type": 103, "mac": DEVICE_MAC}),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_init_cannot_connect_because_of_device_info(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test error handling for failing get_device_info."""
    with (
        patch(
            "pymystrom.get_device_info",
            side_effect=MyStromConnectionError(),
        ),
        patch("pymystrom.switch.MyStromSwitch.get_state", return_value={}),
        patch("pymystrom.bulb.MyStromBulb.get_state", return_value={}),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_init_cannot_connect_because_of_get_state(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test error handling for failing get_state."""
    with (
        patch(
            "pymystrom.get_device_info",
            side_effect=AsyncMock(return_value=get_default_device_response(101)),
        ),
        patch(
            "pymystrom.switch.MyStromSwitch.get_state",
            side_effect=MyStromConnectionError(),
        ),
        patch(
            "pymystrom.bulb.MyStromBulb.get_state", side_effect=MyStromConnectionError()
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
