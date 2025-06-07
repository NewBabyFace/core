"""Test the MenuAI hardware firmware config flow failure cases."""

from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.menuaiio import AddonError, AddonInfo, AddonState
from menuai.components.menuai_hardware.firmware_config_flow import (
    STEP_PICK_FIRMWARE_THREAD,
    STEP_PICK_FIRMWARE_ZIGBEE,
)
from menuai.components.menuai_hardware.util import (
    ApplicationType,
    FirmwareInfo,
    OwningIntegration,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .test_config_flow import (
    TEST_DEVICE,
    TEST_DOMAIN,
    TEST_HARDWARE_NAME,
    delayed_side_effect,
    mock_addon_info,
    mock_test_firmware_platform,  # noqa: F401
)

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
async def fixture_mock_supervisor_client(supervisor_client: AsyncMock):
    """Mock supervisor client in tests."""


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
@pytest.mark.parametrize(
    "next_step",
    [
        STEP_PICK_FIRMWARE_ZIGBEE,
        STEP_PICK_FIRMWARE_THREAD,
    ],
)
@pytest.mark.usefixtures("addon_store_info")
async def test_config_flow_cannot_probe_firmware(
    next_step: str, menuai: menuai
) -> None:
    """Test failure case when firmware cannot be probed."""

    with mock_addon_info(
        menuai,
        app_type=None,
    ) as (mock_otbr_manager, mock_flasher_manager):
        # Start the flow
        result = await menuai.config_entries.flow.async_init(
            TEST_DOMAIN, context={"source": "hardware"}
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": next_step},
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "unsupported_firmware"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_zigbee_not_menuaiio_wrong_firmware(
    menuai: menuai,
) -> None:
    """Test when the stick is used with a non-menuaiio setup but the firmware is bad."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.SPINEL,
        is_menuaiio=False,
    ) as (mock_otbr_manager, mock_flasher_manager):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "not_menuaiio"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_zigbee_flasher_addon_already_running(
    menuai: menuai,
) -> None:
    """Test failure case when flasher addon is already running."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.SPINEL,
        flasher_addon_info=AddonInfo(
            available=True,
            hostname=None,
            options={},
            state=AddonState.RUNNING,
            update_available=False,
            version="1.0.0",
        ),
    ) as (mock_otbr_manager, mock_flasher_manager):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )

        # Cannot get addon info
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_already_running"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_zigbee_flasher_addon_info_fails(menuai: menuai) -> None:
    """Test failure case when flasher addon cannot be installed."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.SPINEL,
        flasher_addon_info=AddonInfo(
            available=True,
            hostname=None,
            options={},
            state=AddonState.RUNNING,
            update_available=False,
            version="1.0.0",
        ),
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_flasher_manager.async_get_addon_info.side_effect = AddonError()

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )

        # Cannot get addon info
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_info_failed"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_zigbee_flasher_addon_install_fails(
    menuai: menuai,
) -> None:
    """Test failure case when flasher addon cannot be installed."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.SPINEL,
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_flasher_manager.async_install_addon_waiting = AsyncMock(
            side_effect=AddonError()
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )

        # Cannot install addon
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_install_failed"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_zigbee_flasher_addon_set_config_fails(
    menuai: menuai,
) -> None:
    """Test failure case when flasher addon cannot be configured."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.SPINEL,
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_flasher_manager.async_install_addon_waiting = AsyncMock(
            side_effect=delayed_side_effect()
        )
        mock_flasher_manager.async_set_addon_options = AsyncMock(
            side_effect=AddonError()
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_set_config_failed"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_zigbee_flasher_run_fails(menuai: menuai) -> None:
    """Test failure case when flasher addon fails to run."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.SPINEL,
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_flasher_manager.async_start_addon_waiting = AsyncMock(
            side_effect=AddonError()
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_start_failed"


async def test_config_flow_zigbee_flasher_uninstall_fails(menuai: menuai) -> None:
    """Test failure case when flasher addon uninstall fails."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.SPINEL,
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_flasher_manager.async_uninstall_addon_waiting = AsyncMock(
            side_effect=AddonError()
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        # Uninstall failure isn't critical
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm_zigbee"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_zigbee_confirmation_fails(menuai: menuai) -> None:
    """Test the config flow failing due to Zigbee firmware not being detected."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "pick_firmware"

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.EZSP,
    ) as (mock_otbr_manager, mock_flasher_manager):
        # Pick the menu option: we are now installing the addon
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm_zigbee"

    with mock_addon_info(
        menuai,
        app_type=None,  # Probing fails
    ) as (mock_otbr_manager, mock_flasher_manager):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "unsupported_firmware"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_thread_not_menuaiio(menuai: menuai) -> None:
    """Test when the stick is used with a non-menuaiio setup and Thread is selected."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        is_menuaiio=False,
        app_type=ApplicationType.EZSP,
    ) as (mock_otbr_manager, mock_flasher_manager):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "not_menuaiio_thread"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_thread_addon_info_fails(menuai: menuai) -> None:
    """Test failure case when flasher addon cannot be installed."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.EZSP,
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_otbr_manager.async_get_addon_info.side_effect = AddonError()
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )

        # Cannot get addon info
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_info_failed"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_thread_addon_already_running(menuai: menuai) -> None:
    """Test failure case when the Thread addon is already running."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.EZSP,
        otbr_addon_info=AddonInfo(
            available=True,
            hostname=None,
            options={},
            state=AddonState.RUNNING,
            update_available=False,
            version="1.0.0",
        ),
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_otbr_manager.async_install_addon_waiting = AsyncMock(
            side_effect=AddonError()
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )

        # Cannot install addon
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "otbr_addon_already_running"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_thread_addon_install_fails(menuai: menuai) -> None:
    """Test failure case when flasher addon cannot be installed."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.EZSP,
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_otbr_manager.async_install_addon_waiting = AsyncMock(
            side_effect=AddonError()
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )

        # Cannot install addon
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_install_failed"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_thread_addon_set_config_fails(menuai: menuai) -> None:
    """Test failure case when flasher addon cannot be configured."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.EZSP,
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_otbr_manager.async_set_addon_options = AsyncMock(side_effect=AddonError())

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_set_config_failed"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_thread_flasher_run_fails(menuai: menuai) -> None:
    """Test failure case when flasher addon fails to run."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.EZSP,
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_otbr_manager.async_start_addon_waiting = AsyncMock(
            side_effect=AddonError()
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "addon_start_failed"


async def test_config_flow_thread_flasher_uninstall_fails(menuai: menuai) -> None:
    """Test failure case when flasher addon uninstall fails."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.EZSP,
    ) as (mock_otbr_manager, mock_flasher_manager):
        mock_otbr_manager.async_uninstall_addon_waiting = AsyncMock(
            side_effect=AddonError()
        )

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        # Uninstall failure isn't critical
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm_otbr"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_config_flow_thread_confirmation_fails(menuai: menuai) -> None:
    """Test the config flow failing due to OpenThread firmware not being detected."""
    result = await menuai.config_entries.flow.async_init(
        TEST_DOMAIN, context={"source": "hardware"}
    )

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.EZSP,
    ) as (mock_otbr_manager, mock_flasher_manager):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done(wait_background_tasks=True)

        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm_otbr"

    with mock_addon_info(
        menuai,
        app_type=None,  # Probing fails
    ) as (mock_otbr_manager, mock_flasher_manager):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "unsupported_firmware"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
async def test_options_flow_zigbee_to_thread_zha_configured(
    menuai: menuai,
) -> None:
    """Test the options flow migration failure, ZHA using the stick."""
    config_entry = MockConfigEntry(
        domain=TEST_DOMAIN,
        data={
            "firmware": "ezsp",
            "device": TEST_DEVICE,
            "hardware": TEST_HARDWARE_NAME,
        },
        version=1,
        minor_version=2,
    )
    config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    # Pretend ZHA is using the stick
    with patch(
        "menuai.components.menuai_hardware.firmware_config_flow.guess_hardware_owners",
        return_value=[
            FirmwareInfo(
                device=TEST_DEVICE,
                firmware_type=ApplicationType.EZSP,
                firmware_version="1.2.3.4",
                source="zha",
                owners=[OwningIntegration(config_entry_id="some_config_entry_id")],
            )
        ],
    ):
        # Confirm options flow
        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

        # Pick Thread
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_THREAD},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "zha_still_using_stick"


@pytest.mark.parametrize(
    "ignore_translations_for_mock_domains",
    ["test_firmware_domain"],
)
@pytest.mark.usefixtures("addon_store_info")
async def test_options_flow_thread_to_zigbee_otbr_configured(
    menuai: menuai,
) -> None:
    """Test the options flow migration failure, OTBR still using the stick."""
    config_entry = MockConfigEntry(
        domain=TEST_DOMAIN,
        data={
            "firmware": "spinel",
            "device": TEST_DEVICE,
            "hardware": TEST_HARDWARE_NAME,
        },
        version=1,
        minor_version=2,
    )
    config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    # Confirm options flow
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    with mock_addon_info(
        menuai,
        app_type=ApplicationType.SPINEL,
        otbr_addon_info=AddonInfo(
            available=True,
            hostname=None,
            options={"device": TEST_DEVICE},
            state=AddonState.RUNNING,
            update_available=False,
            version="1.0.0",
        ),
    ) as (mock_otbr_manager, mock_flasher_manager):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"next_step_id": STEP_PICK_FIRMWARE_ZIGBEE},
        )
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "otbr_still_using_stick"
