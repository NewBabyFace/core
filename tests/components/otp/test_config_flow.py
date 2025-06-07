"""Test the One-Time Password (OTP) config flow."""

import binascii
from unittest.mock import AsyncMock, MagicMock

import pytest

from menuai.components.otp.const import CONF_NEW_TOKEN, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_CODE, CONF_NAME, CONF_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

TEST_DATA = {
    CONF_NAME: "OTP Sensor",
    CONF_TOKEN: "2FX5 FBSY RE6V EC2F SHBQ CRKO 2GND VZ52",
}
TEST_DATA_RESULT = {
    CONF_NAME: "OTP Sensor",
    CONF_TOKEN: "2FX5FBSYRE6VEC2FSHBQCRKO2GNDVZ52",
}

TEST_DATA_2 = {
    CONF_NAME: "OTP Sensor",
    CONF_NEW_TOKEN: True,
}

TEST_DATA_3 = {
    CONF_NAME: "OTP Sensor",
    CONF_TOKEN: "",
}


@pytest.mark.usefixtures("mock_pyotp")
async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_DATA,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "OTP Sensor"
    assert result["data"] == TEST_DATA_RESULT
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (binascii.Error, "invalid_token"),
        (IndexError, "unknown"),
    ],
)
async def test_errors_and_recover(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_pyotp: MagicMock,
    exception: Exception,
    error: str,
) -> None:
    """Test errors and recover."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    mock_pyotp.TOTP().now.side_effect = exception
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=TEST_DATA,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_pyotp.TOTP().now.side_effect = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=TEST_DATA,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "OTP Sensor"
    assert result["data"] == TEST_DATA_RESULT
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("mock_pyotp")
async def test_generate_new_token(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test form generate new token."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_DATA_2,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_CODE: "123456"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "OTP Sensor"
    assert result["data"] == TEST_DATA_RESULT
    assert len(mock_setup_entry.mock_calls) == 1


async def test_generate_new_token_errors(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_pyotp
) -> None:
    """Test input validation errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_DATA_3,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_token"}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_DATA_2,
    )
    mock_pyotp.TOTP().verify.return_value = False
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_CODE: "123456"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_code"}

    mock_pyotp.TOTP().verify.return_value = True
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_CODE: "123456"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "OTP Sensor"
    assert result["data"] == TEST_DATA_RESULT
    assert len(mock_setup_entry.mock_calls) == 1
