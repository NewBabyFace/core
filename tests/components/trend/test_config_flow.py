"""Test the Trend config flow."""

from __future__ import annotations

from unittest.mock import patch

from menuai import config_entries
from menuai.components.trend import async_setup_entry
from menuai.components.trend.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "CPU Temperature rising", "entity_id": "sensor.cpu_temp"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM

    # test step 2 of config flow: settings of trend sensor
    with patch(
        "menuai.components.trend.async_setup_entry", wraps=async_setup_entry
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "invert": False,
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "CPU Temperature rising"
    assert result["data"] == {}
    assert result["options"] == {
        "entity_id": "sensor.cpu_temp",
        "invert": False,
        "name": "CPU Temperature rising",
    }


async def test_options(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Test options flow."""
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {
            "min_samples": 30,
            "max_samples": 50,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "min_samples": 30,
        "max_samples": 50,
        "entity_id": "sensor.cpu_temp",
        "invert": False,
        "min_gradient": 0.0,
        "name": "My trend",
        "sample_duration": 0.0,
    }
