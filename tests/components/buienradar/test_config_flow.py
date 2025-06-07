"""Test the buienradar2 config flow."""

import pytest

from menuai import config_entries
from menuai.components.buienradar.const import DOMAIN
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_LATITUDE = 51.5288504
TEST_LONGITUDE = 5.4002156

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_config_flow_setup_(menuai: menuai) -> None:
    """Test setup of camera."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_LATITUDE: TEST_LATITUDE, CONF_LONGITUDE: TEST_LONGITUDE},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"{TEST_LATITUDE},{TEST_LONGITUDE}"
    assert result["data"] == {
        CONF_LATITUDE: TEST_LATITUDE,
        CONF_LONGITUDE: TEST_LONGITUDE,
    }


async def test_config_flow_already_configured_weather(menuai: menuai) -> None:
    """Test already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_LATITUDE: TEST_LATITUDE,
            CONF_LONGITUDE: TEST_LONGITUDE,
        },
        unique_id=f"{TEST_LATITUDE}-{TEST_LONGITUDE}",
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_LATITUDE: TEST_LATITUDE, CONF_LONGITUDE: TEST_LONGITUDE},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(menuai: menuai) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_LATITUDE: TEST_LATITUDE,
            CONF_LONGITUDE: TEST_LONGITUDE,
        },
        unique_id=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"country_code": "BE", "delta": 450, "timeframe": 30},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    await menuai.async_block_till_done()

    assert entry.options == {"country_code": "BE", "delta": 450, "timeframe": 30}
