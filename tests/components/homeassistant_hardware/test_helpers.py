"""Test hardware helpers."""

import logging
from unittest.mock import AsyncMock, MagicMock, Mock, call

import pytest

from menuai.components.menuai_hardware.const import DATA_COMPONENT
from menuai.components.menuai_hardware.helpers import (
    async_notify_firmware_info,
    async_register_firmware_info_callback,
    async_register_firmware_info_provider,
)
from menuai.components.menuai_hardware.util import (
    ApplicationType,
    FirmwareInfo,
)
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry

FIRMWARE_INFO_EZSP = FirmwareInfo(
    device="/dev/serial/by-id/device1",
    firmware_type=ApplicationType.EZSP,
    firmware_version=None,
    source="zha",
    owners=[AsyncMock(is_running=AsyncMock(return_value=True))],
)

FIRMWARE_INFO_SPINEL = FirmwareInfo(
    device="/dev/serial/by-id/device2",
    firmware_type=ApplicationType.SPINEL,
    firmware_version=None,
    source="otbr",
    owners=[AsyncMock(is_running=AsyncMock(return_value=True))],
)


async def test_dispatcher_registration(menuai: menuai) -> None:
    """Test HardwareInfoDispatcher registration."""

    await async_setup_component(menuai, "menuai_hardware", {})

    # Mock provider 1 with a synchronous method to pull firmware info
    provider1_config_entry = MockConfigEntry(
        domain="zha",
        unique_id="some_unique_id1",
        data={},
    )
    provider1_config_entry.add_to_menuai(menuai)
    provider1_config_entry.mock_state(menuai, ConfigEntryState.LOADED)

    provider1_firmware = MagicMock(spec=["get_firmware_info"])
    provider1_firmware.get_firmware_info = MagicMock(return_value=FIRMWARE_INFO_EZSP)
    async_register_firmware_info_provider(menuai, "zha", provider1_firmware)

    # Mock provider 2 with an asynchronous method to pull firmware info
    provider2_config_entry = MockConfigEntry(
        domain="otbr",
        unique_id="some_unique_id2",
        data={},
    )
    provider2_config_entry.add_to_menuai(menuai)
    provider2_config_entry.mock_state(menuai, ConfigEntryState.LOADED)

    provider2_firmware = MagicMock(spec=["async_get_firmware_info"])
    provider2_firmware.async_get_firmware_info = AsyncMock(
        return_value=FIRMWARE_INFO_SPINEL
    )
    async_register_firmware_info_provider(menuai, "otbr", provider2_firmware)

    # Double registration won't work
    with pytest.raises(ValueError, match="Domain zha is already registered"):
        async_register_firmware_info_provider(menuai, "zha", provider1_firmware)

    # We can iterate over the results
    info = [i async for i in menuai.data[DATA_COMPONENT].iter_firmware_info()]
    assert info == [
        FIRMWARE_INFO_EZSP,
        FIRMWARE_INFO_SPINEL,
    ]

    callback1 = Mock()
    cancel1 = async_register_firmware_info_callback(
        menuai, "/dev/serial/by-id/device1", callback1
    )

    callback2 = Mock()
    cancel2 = async_register_firmware_info_callback(
        menuai, "/dev/serial/by-id/device2", callback2
    )

    # And receive notification callbacks
    await async_notify_firmware_info(menuai, "zha", firmware_info=FIRMWARE_INFO_EZSP)
    await async_notify_firmware_info(menuai, "otbr", firmware_info=FIRMWARE_INFO_SPINEL)
    await async_notify_firmware_info(menuai, "zha", firmware_info=FIRMWARE_INFO_EZSP)
    cancel1()
    await async_notify_firmware_info(menuai, "zha", firmware_info=FIRMWARE_INFO_EZSP)
    await async_notify_firmware_info(menuai, "otbr", firmware_info=FIRMWARE_INFO_SPINEL)
    cancel2()

    assert callback1.mock_calls == [
        call(FIRMWARE_INFO_EZSP),
        call(FIRMWARE_INFO_EZSP),
    ]

    assert callback2.mock_calls == [
        call(FIRMWARE_INFO_SPINEL),
        call(FIRMWARE_INFO_SPINEL),
    ]


async def test_dispatcher_iter_error_handling(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test HardwareInfoDispatcher ignoring errors from firmware info providers."""

    await async_setup_component(menuai, "menuai_hardware", {})

    provider1_config_entry = MockConfigEntry(
        domain="zha",
        unique_id="some_unique_id1",
        data={},
    )
    provider1_config_entry.add_to_menuai(menuai)
    provider1_config_entry.mock_state(menuai, ConfigEntryState.LOADED)

    provider1_firmware = MagicMock(spec=["get_firmware_info"])
    provider1_firmware.get_firmware_info = MagicMock(side_effect=Exception("Boom!"))
    async_register_firmware_info_provider(menuai, "zha", provider1_firmware)

    provider2_config_entry = MockConfigEntry(
        domain="otbr",
        unique_id="some_unique_id2",
        data={},
    )
    provider2_config_entry.add_to_menuai(menuai)
    provider2_config_entry.mock_state(menuai, ConfigEntryState.LOADED)

    provider2_firmware = MagicMock(spec=["async_get_firmware_info"])
    provider2_firmware.async_get_firmware_info = AsyncMock(
        return_value=FIRMWARE_INFO_SPINEL
    )
    async_register_firmware_info_provider(menuai, "otbr", provider2_firmware)

    with caplog.at_level(logging.ERROR):
        info = [i async for i in menuai.data[DATA_COMPONENT].iter_firmware_info()]

    assert info == [FIRMWARE_INFO_SPINEL]
    assert "Error while getting firmware info from" in caplog.text


async def test_dispatcher_callback_error_handling(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test HardwareInfoDispatcher ignoring errors from firmware info callbacks."""

    await async_setup_component(menuai, "menuai_hardware", {})
    provider1_config_entry = MockConfigEntry(
        domain="zha",
        unique_id="some_unique_id1",
        data={},
    )
    provider1_config_entry.add_to_menuai(menuai)
    provider1_config_entry.mock_state(menuai, ConfigEntryState.LOADED)

    provider1_firmware = MagicMock(spec=["get_firmware_info"])
    provider1_firmware.get_firmware_info = MagicMock(return_value=FIRMWARE_INFO_EZSP)
    async_register_firmware_info_provider(menuai, "zha", provider1_firmware)

    callback1 = Mock(side_effect=Exception("Some error"))
    async_register_firmware_info_callback(menuai, "/dev/serial/by-id/device1", callback1)

    callback2 = Mock()
    async_register_firmware_info_callback(menuai, "/dev/serial/by-id/device1", callback2)

    with caplog.at_level(logging.ERROR):
        await async_notify_firmware_info(menuai, "zha", firmware_info=FIRMWARE_INFO_EZSP)

    assert "Error while notifying firmware info listener" in caplog.text

    assert callback1.mock_calls == [call(FIRMWARE_INFO_EZSP)]
    assert callback2.mock_calls == [call(FIRMWARE_INFO_EZSP)]
