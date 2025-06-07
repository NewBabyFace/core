"""Tests for SpeedTest config flow."""

from unittest.mock import MagicMock

from menuai import config_entries
from menuai.components.speedtestdotnet.const import (
    CONF_SERVER_ID,
    CONF_SERVER_NAME,
    DOMAIN,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_flow_works(menuai: menuai) -> None:
    """Test user config."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_options(menuai: menuai, mock_api: MagicMock) -> None:
    """Test updating options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="SpeedTest",
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SERVER_NAME: "Country1 - Sponsor1 - Server1",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SERVER_NAME: "Country1 - Sponsor1 - Server1",
        CONF_SERVER_ID: "1",
    }
    await menuai.async_block_till_done()

    # test setting server name to "*Auto Detect"
    result = await menuai.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SERVER_NAME: "*Auto Detect",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SERVER_NAME: "*Auto Detect",
        CONF_SERVER_ID: None,
    }


async def test_integration_already_configured(menuai: menuai) -> None:
    """Test integration is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
