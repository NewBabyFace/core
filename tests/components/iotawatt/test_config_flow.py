"""Test the IoTawatt config flow."""

from unittest.mock import patch

import httpx

from menuai import config_entries
from menuai.components.iotawatt.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == config_entries.SOURCE_USER

    with (
        patch(
            "menuai.components.iotawatt.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.iotawatt.config_flow.Iotawatt.connect",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 1
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        "host": "1.1.1.1",
    }


async def test_form_auth(menuai: menuai) -> None:
    """Test we handle auth."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "menuai.components.iotawatt.config_flow.Iotawatt.connect",
        return_value=False,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "1.1.1.1"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "auth"

    with patch(
        "menuai.components.iotawatt.config_flow.Iotawatt.connect",
        return_value=False,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "mock-user",
                "password": "mock-pass",
            },
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.FORM
    assert result3["step_id"] == "auth"
    assert result3["errors"] == {"base": "invalid_auth"}

    with (
        patch(
            "menuai.components.iotawatt.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.iotawatt.config_flow.Iotawatt.connect",
            return_value=True,
        ),
    ):
        result4 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "mock-user",
                "password": "mock-pass",
            },
        )
        await menuai.async_block_till_done()

    assert result4["type"] is FlowResultType.CREATE_ENTRY
    assert len(mock_setup_entry.mock_calls) == 1
    assert result4["data"] == {
        "host": "1.1.1.1",
        "username": "mock-user",
        "password": "mock-pass",
    }


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.iotawatt.config_flow.Iotawatt.connect",
        side_effect=httpx.HTTPError("any"),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "1.1.1.1"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_setup_exception(menuai: menuai) -> None:
    """Test we handle broad exception."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.iotawatt.config_flow.Iotawatt.connect",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "1.1.1.1"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}
