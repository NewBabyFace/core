"""Test the acaia config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

from aioacaia.exceptions import AcaiaDeviceNotFound, AcaiaError, AcaiaUnknownDevice
import pytest

from menuai.components.acaia.const import CONF_IS_NEW_STYLE_SCALE, DOMAIN
from menuai.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from menuai.const import CONF_ADDRESS
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.bluetooth import BluetoothServiceInfo

from tests.common import MockConfigEntry

service_info = BluetoothServiceInfo(
    name="LUNAR-DDEEFF",
    address="aa:bb:cc:dd:ee:ff",
    rssi=-63,
    manufacturer_data={},
    service_data={},
    service_uuids=[],
    source="local",
)


@pytest.fixture
def mock_discovered_service_info() -> Generator[AsyncMock]:
    """Override getting Bluetooth service info."""
    with patch(
        "menuai.components.acaia.config_flow.async_discovered_service_info",
        return_value=[service_info],
    ) as mock_discovered_service_info:
        yield mock_discovered_service_info


async def test_form(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_verify: AsyncMock,
    mock_discovered_service_info: AsyncMock,
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    user_input = {
        CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
    }
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_input,
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "LUNAR-DDEEFF"
    assert result2["data"] == {
        **user_input,
        CONF_IS_NEW_STYLE_SCALE: True,
    }


async def test_bluetooth_discovery(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_verify: AsyncMock,
) -> None:
    """Test we can discover a device."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=service_info
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == service_info.name
    assert result2["data"] == {
        CONF_ADDRESS: service_info.address,
        CONF_IS_NEW_STYLE_SCALE: True,
    }


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (AcaiaDeviceNotFound("Error"), "device_not_found"),
        (AcaiaError, "unknown"),
        (AcaiaUnknownDevice, "unsupported_device"),
    ],
)
async def test_bluetooth_discovery_errors(
    menuai: menuai,
    mock_verify: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test abortions of Bluetooth discovery."""
    mock_verify.side_effect = exception

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=service_info
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == error


async def test_already_configured(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_verify: AsyncMock,
    mock_discovered_service_info: AsyncMock,
) -> None:
    """Ensure we can't add the same device twice."""

    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        },
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_already_configured_bluetooth_discovery(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Ensure configure device is not discovered again."""

    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=service_info
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (AcaiaDeviceNotFound("Error"), "device_not_found"),
        (AcaiaError, "unknown"),
    ],
)
async def test_recoverable_config_flow_errors(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_verify: AsyncMock,
    mock_discovered_service_info: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test recoverable errors."""
    mock_verify.side_effect = exception
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        },
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": error}

    # recover
    mock_verify.side_effect = None
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        },
    )
    assert result3["type"] is FlowResultType.CREATE_ENTRY


async def test_unsupported_device(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_verify: AsyncMock,
    mock_discovered_service_info: AsyncMock,
) -> None:
    """Test flow aborts on unsupported device."""
    mock_verify.side_effect = AcaiaUnknownDevice
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        },
    )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "unsupported_device"


async def test_no_bluetooth_devices(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_discovered_service_info: AsyncMock,
) -> None:
    """Test flow aborts on unsupported device."""
    mock_discovered_service_info.return_value = []

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"
