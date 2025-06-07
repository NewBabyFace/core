"""Test MenuAI Hardware platform for OTBR."""

from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from menuai.components.menuai_hardware.helpers import (
    async_register_firmware_info_callback,
)
from menuai.components.menuai_hardware.util import (
    ApplicationType,
    FirmwareInfo,
    OwningAddon,
    OwningIntegration,
)
from menuai.components.otbr.menuai_hardware import async_get_firmware_info
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.setup import async_setup_component

from . import TEST_COPROCESSOR_VERSION

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker

DEVICE_PATH = "/dev/serial/by-id/usb-Nabu_Casa_Home_Assistant_Connect_ZBT-1_9ab1da1ea4b3ed11956f4eaca7669f5d-if00-port0"


async def test_get_firmware_info(menuai: menuai) -> None:
    """Test `async_get_firmware_info`."""

    otbr = MockConfigEntry(
        domain="otbr",
        unique_id="some_unique_id",
        data={
            "url": "http://core_openthread_border_router:8888",
        },
        version=1,
    )
    otbr.add_to_menuai(menuai)
    otbr.mock_state(menuai, ConfigEntryState.LOADED)

    otbr.runtime_data = AsyncMock()
    otbr.runtime_data.get_coprocessor_version.return_value = TEST_COPROCESSOR_VERSION

    with (
        patch(
            "menuai.components.otbr.menuai_hardware.is_menuaiio",
            return_value=True,
        ),
        patch(
            "menuai.components.otbr.menuai_hardware.AddonManager",
        ),
        patch(
            "menuai.components.otbr.menuai_hardware.get_otbr_addon_firmware_info",
            return_value=FirmwareInfo(
                device=DEVICE_PATH,
                firmware_type=ApplicationType.SPINEL,
                firmware_version=None,
                source="otbr",
                owners=[
                    OwningAddon(slug="core_openthread_border_router"),
                ],
            ),
        ),
    ):
        fw_info = await async_get_firmware_info(menuai, otbr)

    assert fw_info == FirmwareInfo(
        device=DEVICE_PATH,
        firmware_type=ApplicationType.SPINEL,
        firmware_version=TEST_COPROCESSOR_VERSION,
        source="otbr",
        owners=[
            OwningIntegration(config_entry_id=otbr.entry_id),
            OwningAddon(slug="core_openthread_border_router"),
        ],
    )


async def test_get_firmware_info_ignored(menuai: menuai) -> None:
    """Test `async_get_firmware_info` with ignored entry."""

    otbr = MockConfigEntry(
        domain="otbr",
        unique_id="some_unique_id",
        data={},
        version=1,
    )
    otbr.add_to_menuai(menuai)

    fw_info = await async_get_firmware_info(menuai, otbr)
    assert fw_info is None


async def test_get_firmware_info_no_coprocessor_version(menuai: menuai) -> None:
    """Test `async_get_firmware_info` with no coprocessor version support."""

    otbr = MockConfigEntry(
        domain="otbr",
        unique_id="some_unique_id",
        data={
            "url": "http://core_openthread_border_router:8888",
        },
        version=1,
    )
    otbr.add_to_menuai(menuai)
    otbr.mock_state(menuai, ConfigEntryState.LOADED)

    otbr.runtime_data = AsyncMock()
    otbr.runtime_data.get_coprocessor_version.side_effect = menuaiError()

    with (
        patch(
            "menuai.components.otbr.menuai_hardware.is_menuaiio",
            return_value=True,
        ),
        patch(
            "menuai.components.otbr.menuai_hardware.AddonManager",
        ),
        patch(
            "menuai.components.otbr.menuai_hardware.get_otbr_addon_firmware_info",
            return_value=FirmwareInfo(
                device=DEVICE_PATH,
                firmware_type=ApplicationType.SPINEL,
                firmware_version=None,
                source="otbr",
                owners=[
                    OwningAddon(slug="core_openthread_border_router"),
                ],
            ),
        ),
    ):
        fw_info = await async_get_firmware_info(menuai, otbr)

    assert fw_info == FirmwareInfo(
        device=DEVICE_PATH,
        firmware_type=ApplicationType.SPINEL,
        firmware_version=None,
        source="otbr",
        owners=[
            OwningIntegration(config_entry_id=otbr.entry_id),
            OwningAddon(slug="core_openthread_border_router"),
        ],
    )


@pytest.mark.parametrize(
    ("version", "expected_version"),
    [
        ((TEST_COPROCESSOR_VERSION,), TEST_COPROCESSOR_VERSION),
        (menuaiError(), None),
    ],
)
async def test_hardware_firmware_info_provider_notification(
    menuai: menuai,
    version: str | Exception,
    expected_version: str | None,
    get_active_dataset_tlvs: AsyncMock,
    get_border_agent_id: AsyncMock,
    get_extended_address: AsyncMock,
    get_coprocessor_version: AsyncMock,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test that the OTBR provides hardware and firmware information."""
    otbr = MockConfigEntry(
        domain="otbr",
        unique_id="some_unique_id",
        data={
            "url": "http://core_openthread_border_router:8888",
        },
        version=1,
    )
    otbr.add_to_menuai(menuai)

    await async_setup_component(menuai, "menuai_hardware", {})

    callback = Mock()
    async_register_firmware_info_callback(menuai, DEVICE_PATH, callback)

    with (
        patch(
            "menuai.components.otbr.menuai_hardware.is_menuaiio",
            return_value=True,
        ),
        patch(
            "menuai.components.otbr.menuai_hardware.AddonManager",
        ),
        patch(
            "menuai.components.otbr.menuai_hardware.get_otbr_addon_firmware_info",
            return_value=FirmwareInfo(
                device=DEVICE_PATH,
                firmware_type=ApplicationType.SPINEL,
                firmware_version=None,
                source="otbr",
                owners=[
                    OwningAddon(slug="core_openthread_border_router"),
                ],
            ),
        ),
    ):
        get_coprocessor_version.side_effect = version
        await menuai.config_entries.async_setup(otbr.entry_id)

    assert callback.mock_calls == [
        call(
            FirmwareInfo(
                device=DEVICE_PATH,
                firmware_type=ApplicationType.SPINEL,
                firmware_version=expected_version,
                source="otbr",
                owners=[
                    OwningIntegration(config_entry_id=otbr.entry_id),
                    OwningAddon(slug="core_openthread_border_router"),
                ],
            )
        )
    ]


async def test_get_firmware_info_remote_otbr(menuai: menuai) -> None:
    """Test `async_get_firmware_info` with no coprocessor version support."""

    otbr = MockConfigEntry(
        domain="otbr",
        unique_id="some_unique_id",
        data={
            "url": "http://192.168.1.10:8888",
        },
        version=1,
    )
    otbr.add_to_menuai(menuai)
    otbr.mock_state(menuai, ConfigEntryState.LOADED)

    otbr.runtime_data = AsyncMock()
    otbr.runtime_data.get_coprocessor_version.return_value = TEST_COPROCESSOR_VERSION

    with (
        patch(
            "menuai.components.otbr.menuai_hardware.is_menuaiio",
            return_value=True,
        ),
        patch(
            "menuai.components.otbr.menuai_hardware.AddonManager",
        ),
        patch(
            "menuai.components.otbr.menuai_hardware.get_otbr_addon_firmware_info",
            return_value=None,
        ),
    ):
        fw_info = await async_get_firmware_info(menuai, otbr)

    assert fw_info is None
