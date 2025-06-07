"""Test the Opentherm Gateway config flow."""

from unittest.mock import AsyncMock, MagicMock

from serial import SerialException

from menuai import config_entries
from menuai.components.opentherm_gw.const import (
    CONF_FLOOR_TEMP,
    CONF_READ_PRECISION,
    CONF_SET_PRECISION,
    CONF_TEMPORARY_OVRD_MODE,
    DOMAIN,
)
from menuai.const import (
    CONF_DEVICE,
    CONF_ID,
    CONF_NAME,
    PRECISION_HALVES,
    PRECISION_TENTHS,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form_user(
    menuai: menuai,
    mock_pyotgw: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Test Entry 1", CONF_DEVICE: "/dev/ttyUSB0"}
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test Entry 1"
    assert result2["data"] == {
        CONF_NAME: "Test Entry 1",
        CONF_DEVICE: "/dev/ttyUSB0",
        CONF_ID: "test_entry_1",
    }
    assert mock_pyotgw.return_value.connect.await_count == 1
    assert mock_pyotgw.return_value.disconnect.await_count == 1


async def test_form_duplicate_entries(
    menuai: menuai,
    mock_pyotgw: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test duplicate device or id errors."""
    flow1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    flow2 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    flow3 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result1 = await menuai.config_entries.flow.async_configure(
        flow1["flow_id"], {CONF_NAME: "Test Entry 1", CONF_DEVICE: "/dev/ttyUSB0"}
    )
    assert result1["type"] is FlowResultType.CREATE_ENTRY

    result2 = await menuai.config_entries.flow.async_configure(
        flow2["flow_id"], {CONF_NAME: "Test Entry 1", CONF_DEVICE: "/dev/ttyUSB1"}
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "id_exists"}

    result3 = await menuai.config_entries.flow.async_configure(
        flow3["flow_id"], {CONF_NAME: "Test Entry 2", CONF_DEVICE: "/dev/ttyUSB0"}
    )
    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {"base": "already_configured"}

    assert mock_pyotgw.return_value.connect.await_count == 1
    assert mock_pyotgw.return_value.disconnect.await_count == 1


async def test_form_connection_timeout(
    menuai: menuai,
    mock_pyotgw: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we handle connection timeout."""
    flow = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_pyotgw.return_value.connect.side_effect = TimeoutError

    result = await menuai.config_entries.flow.async_configure(
        flow["flow_id"],
        {CONF_NAME: "Test Entry 1", CONF_DEVICE: "socket://192.0.2.254:1234"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "timeout_connect"}

    assert mock_pyotgw.return_value.connect.await_count == 1


async def test_form_connection_error(
    menuai: menuai,
    mock_pyotgw: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we handle serial connection error."""
    flow = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_pyotgw.return_value.connect.side_effect = SerialException

    result = await menuai.config_entries.flow.async_configure(
        flow["flow_id"], {CONF_NAME: "Test Entry 1", CONF_DEVICE: "/dev/ttyUSB0"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert mock_pyotgw.return_value.connect.await_count == 1


async def test_options_form(
    menuai: menuai,
    mock_pyotgw: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the options form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Mock Gateway",
        data={
            CONF_NAME: "Mock Gateway",
            CONF_DEVICE: "/dev/null",
            CONF_ID: "mock_gateway",
        },
        options={},
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    flow = await menuai.config_entries.options.async_init(
        entry.entry_id, context={"source": "test"}, data=None
    )
    assert flow["type"] is FlowResultType.FORM
    assert flow["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={
            CONF_FLOOR_TEMP: True,
            CONF_READ_PRECISION: PRECISION_HALVES,
            CONF_SET_PRECISION: PRECISION_HALVES,
            CONF_TEMPORARY_OVRD_MODE: True,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_READ_PRECISION] == PRECISION_HALVES
    assert result["data"][CONF_SET_PRECISION] == PRECISION_HALVES
    assert result["data"][CONF_TEMPORARY_OVRD_MODE] is True
    assert result["data"][CONF_FLOOR_TEMP] is True

    flow = await menuai.config_entries.options.async_init(
        entry.entry_id, context={"source": "test"}, data=None
    )

    result = await menuai.config_entries.options.async_configure(
        flow["flow_id"], user_input={CONF_READ_PRECISION: 0}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_READ_PRECISION] == 0.0
    assert result["data"][CONF_SET_PRECISION] == PRECISION_HALVES
    assert result["data"][CONF_TEMPORARY_OVRD_MODE] is True
    assert result["data"][CONF_FLOOR_TEMP] is True

    flow = await menuai.config_entries.options.async_init(
        entry.entry_id, context={"source": "test"}, data=None
    )

    result = await menuai.config_entries.options.async_configure(
        flow["flow_id"],
        user_input={
            CONF_FLOOR_TEMP: False,
            CONF_READ_PRECISION: PRECISION_TENTHS,
            CONF_SET_PRECISION: PRECISION_HALVES,
            CONF_TEMPORARY_OVRD_MODE: False,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_READ_PRECISION] == PRECISION_TENTHS
    assert result["data"][CONF_SET_PRECISION] == PRECISION_HALVES
    assert result["data"][CONF_TEMPORARY_OVRD_MODE] is False
    assert result["data"][CONF_FLOOR_TEMP] is False
