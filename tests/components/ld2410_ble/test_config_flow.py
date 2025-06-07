"""Test the LD2410 BLE Bluetooth config flow."""

from unittest.mock import patch

from bleak import BleakError

from menuai import config_entries
from menuai.components.ld2410_ble.const import DOMAIN
from menuai.const import CONF_ADDRESS
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import LD2410_BLE_DISCOVERY_INFO, NOT_LD2410_BLE_DISCOVERY_INFO

from tests.common import MockConfigEntry


async def test_user_step_success(menuai: menuai) -> None:
    """Test user step success path."""
    with patch(
        "menuai.components.ld2410_ble.config_flow.async_discovered_service_info",
        return_value=[NOT_LD2410_BLE_DISCOVERY_INFO, LD2410_BLE_DISCOVERY_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.ld2410_ble.config_flow.LD2410BLE.initialise",
        ),
        patch(
            "menuai.components.ld2410_ble.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == LD2410_BLE_DISCOVERY_INFO.name
    assert result2["data"] == {
        CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
    }
    assert result2["result"].unique_id == LD2410_BLE_DISCOVERY_INFO.address
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_step_no_devices_found(menuai: menuai) -> None:
    """Test user step with no devices found."""
    with patch(
        "menuai.components.ld2410_ble.config_flow.async_discovered_service_info",
        return_value=[NOT_LD2410_BLE_DISCOVERY_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_user_step_no_new_devices_found(menuai: menuai) -> None:
    """Test user step with only existing devices found."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
        },
        unique_id=LD2410_BLE_DISCOVERY_INFO.address,
    )
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.ld2410_ble.config_flow.async_discovered_service_info",
        return_value=[LD2410_BLE_DISCOVERY_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_user_step_cannot_connect(menuai: menuai) -> None:
    """Test user step and we cannot connect."""
    with patch(
        "menuai.components.ld2410_ble.config_flow.async_discovered_service_info",
        return_value=[LD2410_BLE_DISCOVERY_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.ld2410_ble.config_flow.LD2410BLE.initialise",
        side_effect=BleakError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "cannot_connect"}

    with (
        patch(
            "menuai.components.ld2410_ble.config_flow.LD2410BLE.initialise",
        ),
        patch(
            "menuai.components.ld2410_ble.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
            },
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == LD2410_BLE_DISCOVERY_INFO.name
    assert result3["data"] == {
        CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
    }
    assert result3["result"].unique_id == LD2410_BLE_DISCOVERY_INFO.address
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_step_unknown_exception(menuai: menuai) -> None:
    """Test user step with an unknown exception."""
    with patch(
        "menuai.components.ld2410_ble.config_flow.async_discovered_service_info",
        return_value=[NOT_LD2410_BLE_DISCOVERY_INFO, LD2410_BLE_DISCOVERY_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.ld2410_ble.config_flow.LD2410BLE.initialise",
        side_effect=RuntimeError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "unknown"}

    with (
        patch(
            "menuai.components.ld2410_ble.config_flow.LD2410BLE.initialise",
        ),
        patch(
            "menuai.components.ld2410_ble.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
            },
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == LD2410_BLE_DISCOVERY_INFO.name
    assert result3["data"] == {
        CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
    }
    assert result3["result"].unique_id == LD2410_BLE_DISCOVERY_INFO.address
    assert len(mock_setup_entry.mock_calls) == 1


async def test_bluetooth_step_success(menuai: menuai) -> None:
    """Test bluetooth step success path."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=LD2410_BLE_DISCOVERY_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.ld2410_ble.config_flow.LD2410BLE.initialise",
        ),
        patch(
            "menuai.components.ld2410_ble.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == LD2410_BLE_DISCOVERY_INFO.name
    assert result2["data"] == {
        CONF_ADDRESS: LD2410_BLE_DISCOVERY_INFO.address,
    }
    assert result2["result"].unique_id == LD2410_BLE_DISCOVERY_INFO.address
    assert len(mock_setup_entry.mock_calls) == 1
