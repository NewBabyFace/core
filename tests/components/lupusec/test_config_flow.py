"""Unit tests for the Lupusec config flow."""

from json import JSONDecodeError
from unittest.mock import patch

from lupupy import LupusecException
import pytest

from menuai import config_entries
from menuai.components.lupusec.const import DOMAIN
from menuai.const import (
    CONF_HOST,
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

MOCK_DATA_STEP = {
    CONF_HOST: "test-host.lan",
    CONF_USERNAME: "test-username",
    CONF_PASSWORD: "test-password",
}

MOCK_IMPORT_STEP = {
    CONF_IP_ADDRESS: "test-host.lan",
    CONF_USERNAME: "test-username",
    CONF_PASSWORD: "test-password",
}

MOCK_IMPORT_STEP_NAME = {
    CONF_IP_ADDRESS: "test-host.lan",
    CONF_USERNAME: "test-username",
    CONF_PASSWORD: "test-password",
    CONF_NAME: "test-name",
}


async def test_form_valid_input(menuai: menuai) -> None:
    """Test handling valid user input."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.lupusec.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.lupusec.config_flow.lupupy.Lupusec",
        ) as mock_initialize_lupusec,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_DATA_STEP,
        )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == MOCK_DATA_STEP[CONF_HOST]
    assert result2["data"] == MOCK_DATA_STEP
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_initialize_lupusec.mock_calls) == 1


@pytest.mark.parametrize(
    ("raise_error", "text_error"),
    [
        (LupusecException("Test lupusec exception"), "cannot_connect"),
        (JSONDecodeError("Test JSONDecodeError", "test", 1), "cannot_connect"),
        (Exception("Test unknown exception"), "unknown"),
    ],
)
async def test_flow_user_init_data_error_and_recover(
    menuai: menuai, raise_error, text_error
) -> None:
    """Test exceptions and recovery."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.lupusec.config_flow.lupupy.Lupusec",
        side_effect=raise_error,
    ) as mock_initialize_lupusec:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_DATA_STEP,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": text_error}

    assert len(mock_initialize_lupusec.mock_calls) == 1

    # Recover
    with (
        patch(
            "menuai.components.lupusec.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.lupusec.config_flow.lupupy.Lupusec",
        ) as mock_initialize_lupusec,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            MOCK_DATA_STEP,
        )

    await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == MOCK_DATA_STEP[CONF_HOST]
    assert result3["data"] == MOCK_DATA_STEP
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_initialize_lupusec.mock_calls) == 1


async def test_flow_user_init_data_already_configured(menuai: menuai) -> None:
    """Test duplicate config entry.."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_DATA_STEP[CONF_HOST],
        data=MOCK_DATA_STEP,
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        MOCK_DATA_STEP,
    )

    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
