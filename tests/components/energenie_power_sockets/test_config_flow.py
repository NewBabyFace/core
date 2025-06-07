"""Tests for Energenie-Power-Sockets config flow."""

from unittest.mock import MagicMock

from pyegps.exceptions import UsbError

from menuai.components.energenie_power_sockets.const import (
    CONF_DEVICE_API_ID,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_user_flow(
    menuai: menuai,
    demo_config_data: dict,
    mock_get_device: MagicMock,
    mock_search_for_devices: MagicMock,
) -> None:
    """Test configuration flow initialized by the user."""

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result1["type"] is FlowResultType.FORM
    assert not result1["errors"]

    # check with valid data
    result2 = await menuai.config_entries.flow.async_configure(
        result1["flow_id"], user_input=demo_config_data
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_exists(
    menuai: menuai,
    valid_config_entry: MockConfigEntry,
    mock_get_device: MagicMock,
    mock_search_for_devices: MagicMock,
) -> None:
    """Test the flow when device has been already configured."""
    valid_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_DEVICE_API_ID: valid_config_entry.data[CONF_DEVICE_API_ID]},
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_no_new_device(
    menuai: menuai,
    valid_config_entry: MockConfigEntry,
    mock_get_device: MagicMock,
    mock_search_for_devices: MagicMock,
) -> None:
    """Test the flow when the found device has been already included."""
    valid_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=None,
    )

    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_device"


async def test_user_flow_no_device_found(
    menuai: menuai,
    demo_config_data: dict,
    mock_get_device: MagicMock,
    mock_search_for_devices: MagicMock,
) -> None:
    """Test configuration flow when no device is found."""

    mock_search_for_devices.return_value = []

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result1["type"] is FlowResultType.ABORT
    assert result1["reason"] == "no_device"


async def test_user_flow_device_not_found(
    menuai: menuai,
    demo_config_data: dict,
    mock_get_device: MagicMock,
    mock_search_for_devices: MagicMock,
) -> None:
    """Test configuration flow when the given device_id does not match any found devices."""

    mock_get_device.return_value = None

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result1["type"] is FlowResultType.FORM
    assert not result1["errors"]

    # check with valid data
    result2 = await menuai.config_entries.flow.async_configure(
        result1["flow_id"], user_input=demo_config_data
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "device_not_found"


async def test_user_flow_no_usb_access(
    menuai: menuai,
    mock_get_device: MagicMock,
    mock_search_for_devices: MagicMock,
) -> None:
    """Test configuration flow when USB devices can't be accessed."""

    mock_get_device.return_value = None
    mock_search_for_devices.side_effect = UsbError

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result1["type"] is FlowResultType.ABORT
    assert result1["reason"] == "usb_error"
