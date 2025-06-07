"""Tests for the Rova config flow."""

from unittest.mock import MagicMock

import pytest
from requests.exceptions import ConnectTimeout, HTTPError

from menuai.components.rova.const import (
    CONF_HOUSE_NUMBER,
    CONF_HOUSE_NUMBER_SUFFIX,
    CONF_ZIP_CODE,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

ZIP_CODE = "7991AD"
HOUSE_NUMBER = "10"
HOUSE_NUMBER_SUFFIX = "a"


async def test_user(menuai: menuai, mock_rova: MagicMock) -> None:
    """Test user config."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    # test with all information provided
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_ZIP_CODE: ZIP_CODE,
            CONF_HOUSE_NUMBER: HOUSE_NUMBER,
            CONF_HOUSE_NUMBER_SUFFIX: HOUSE_NUMBER_SUFFIX,
        },
    )
    assert result.get("type") is FlowResultType.CREATE_ENTRY

    data = result.get("data")
    assert data
    assert data[CONF_ZIP_CODE] == ZIP_CODE
    assert data[CONF_HOUSE_NUMBER] == HOUSE_NUMBER
    assert data[CONF_HOUSE_NUMBER_SUFFIX] == HOUSE_NUMBER_SUFFIX


async def test_error_if_not_rova_area(
    menuai: menuai, mock_rova: MagicMock
) -> None:
    """Test we raise errors if rova does not collect at the given address."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    # test with area where rova does not collect
    mock_rova.return_value.is_rova_area.return_value = False

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ZIP_CODE: ZIP_CODE,
            CONF_HOUSE_NUMBER: HOUSE_NUMBER,
            CONF_HOUSE_NUMBER_SUFFIX: HOUSE_NUMBER_SUFFIX,
        },
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": "invalid_rova_area"}

    # now reset the return value and test if we can recover
    mock_rova.return_value.is_rova_area.return_value = True

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ZIP_CODE: ZIP_CODE,
            CONF_HOUSE_NUMBER: HOUSE_NUMBER,
            CONF_HOUSE_NUMBER_SUFFIX: HOUSE_NUMBER_SUFFIX,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"{ZIP_CODE} {HOUSE_NUMBER} {HOUSE_NUMBER_SUFFIX}"
    assert result["data"] == {
        CONF_ZIP_CODE: ZIP_CODE,
        CONF_HOUSE_NUMBER: HOUSE_NUMBER,
        CONF_HOUSE_NUMBER_SUFFIX: HOUSE_NUMBER_SUFFIX,
    }


async def test_abort_if_already_setup(menuai: menuai) -> None:
    """Test we abort if rova is already setup."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{ZIP_CODE}{HOUSE_NUMBER}{HOUSE_NUMBER_SUFFIX}",
        data={
            CONF_ZIP_CODE: ZIP_CODE,
            CONF_HOUSE_NUMBER: HOUSE_NUMBER,
            CONF_HOUSE_NUMBER_SUFFIX: HOUSE_NUMBER_SUFFIX,
        },
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_ZIP_CODE: ZIP_CODE,
            CONF_HOUSE_NUMBER: HOUSE_NUMBER,
            CONF_HOUSE_NUMBER_SUFFIX: HOUSE_NUMBER_SUFFIX,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (ConnectTimeout(), "cannot_connect"),
        (HTTPError(), "cannot_connect"),
    ],
)
async def test_abort_if_api_throws_exception(
    menuai: menuai, exception: Exception, error: str, mock_rova: MagicMock
) -> None:
    """Test different exceptions for the Rova entity."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    # test with exception
    mock_rova.return_value.is_rova_area.side_effect = exception

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ZIP_CODE: ZIP_CODE,
            CONF_HOUSE_NUMBER: HOUSE_NUMBER,
            CONF_HOUSE_NUMBER_SUFFIX: HOUSE_NUMBER_SUFFIX,
        },
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": error}

    # now reset the side effect to see if we can recover
    mock_rova.return_value.is_rova_area.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ZIP_CODE: ZIP_CODE,
            CONF_HOUSE_NUMBER: HOUSE_NUMBER,
            CONF_HOUSE_NUMBER_SUFFIX: HOUSE_NUMBER_SUFFIX,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"{ZIP_CODE} {HOUSE_NUMBER} {HOUSE_NUMBER_SUFFIX}"
    assert result["data"] == {
        CONF_ZIP_CODE: ZIP_CODE,
        CONF_HOUSE_NUMBER: HOUSE_NUMBER,
        CONF_HOUSE_NUMBER_SUFFIX: HOUSE_NUMBER_SUFFIX,
    }
