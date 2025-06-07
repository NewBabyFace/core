"""Test MenuAI Hardware platform for ZHA."""

from unittest.mock import MagicMock, patch

import pytest
from zigpy.application import ControllerApplication

from menuai.components.menuai_hardware.helpers import (
    async_register_firmware_info_callback,
)
from menuai.components.menuai_hardware.util import (
    ApplicationType,
    FirmwareInfo,
    OwningIntegration,
)
from menuai.components.zha.menuai_hardware import get_firmware_info
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_get_firmware_info_normal(menuai: menuai) -> None:
    """Test `get_firmware_info`."""

    zha = MockConfigEntry(
        domain="zha",
        unique_id="some_unique_id",
        data={
            "device": {
                "path": "/dev/ttyUSB1",
                "baudrate": 115200,
                "flow_control": None,
            },
            "radio_type": "ezsp",
        },
        version=4,
    )
    zha.add_to_menuai(menuai)
    zha.mock_state(menuai, ConfigEntryState.LOADED)

    # With ZHA running
    with patch(
        "menuai.components.zha.menuai_hardware.get_zha_gateway"
    ) as mock_get_zha_gateway:
        mock_get_zha_gateway.return_value.state.node_info.version = "1.2.3.4"
        fw_info_running = get_firmware_info(menuai, zha)

    assert fw_info_running == FirmwareInfo(
        device="/dev/ttyUSB1",
        firmware_type=ApplicationType.EZSP,
        firmware_version="1.2.3.4",
        source="zha",
        owners=[OwningIntegration(config_entry_id=zha.entry_id)],
    )
    assert await fw_info_running.is_running(menuai) is True

    # With ZHA not running
    zha.mock_state(menuai, ConfigEntryState.NOT_LOADED)
    fw_info_not_running = get_firmware_info(menuai, zha)

    assert fw_info_not_running == FirmwareInfo(
        device="/dev/ttyUSB1",
        firmware_type=ApplicationType.EZSP,
        firmware_version=None,
        source="zha",
        owners=[OwningIntegration(config_entry_id=zha.entry_id)],
    )
    assert await fw_info_not_running.is_running(menuai) is False


@pytest.mark.parametrize(
    "data",
    [
        # Missing data
        {},
        # Bad radio type
        {"device": {"path": "/dev/ttyUSB1"}, "radio_type": "znp"},
    ],
)
async def test_get_firmware_info_errors(
    menuai: menuai, data: dict[str, str | int | None]
) -> None:
    """Test `get_firmware_info` with config entry data format errors."""
    zha = MockConfigEntry(
        domain="zha",
        unique_id="some_unique_id",
        data=data,
        version=4,
    )
    zha.add_to_menuai(menuai)

    assert (get_firmware_info(menuai, zha)) is None


async def test_hardware_firmware_info_provider_notification(
    menuai: menuai,
    config_entry: MockConfigEntry,
    mock_zigpy_connect: ControllerApplication,
) -> None:
    """Test that the ZHA gateway provides hardware and firmware information."""
    config_entry.add_to_menuai(menuai)

    await async_setup_component(menuai, "menuai_hardware", {})

    callback = MagicMock()
    async_register_firmware_info_callback(menuai, "/dev/ttyUSB0", callback)

    await menuai.config_entries.async_setup(config_entry.entry_id)

    callback.assert_called_once_with(
        FirmwareInfo(
            device="/dev/ttyUSB0",
            firmware_type=ApplicationType.EZSP,
            firmware_version="7.1.4.0 build 389",
            source="zha",
            owners=[OwningIntegration(config_entry_id=config_entry.entry_id)],
        )
    )
