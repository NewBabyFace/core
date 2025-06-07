"""Test the zerproc config flow."""

from unittest.mock import patch

import pyzerproc

from menuai import config_entries
from menuai.components.zerproc.config_flow import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_flow_success(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "menuai.components.zerproc.config_flow.pyzerproc.discover",
            return_value=["Light1", "Light2"],
        ),
        patch(
            "menuai.components.zerproc.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Zerproc"
    assert result2["data"] == {}

    assert len(mock_setup_entry.mock_calls) == 1


async def test_flow_no_devices_found(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "menuai.components.zerproc.config_flow.pyzerproc.discover",
            return_value=[],
        ),
        patch(
            "menuai.components.zerproc.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "no_devices_found"
    await menuai.async_block_till_done()
    assert len(mock_setup_entry.mock_calls) == 0


async def test_flow_exceptions_caught(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "menuai.components.zerproc.config_flow.pyzerproc.discover",
            side_effect=pyzerproc.ZerprocException("TEST"),
        ),
        patch(
            "menuai.components.zerproc.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "no_devices_found"
    await menuai.async_block_till_done()
    assert len(mock_setup_entry.mock_calls) == 0
