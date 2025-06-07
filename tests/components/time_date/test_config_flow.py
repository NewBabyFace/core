"""Test the Time & Date config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
import pytest
import voluptuous as vol

from menuai import config_entries
from menuai.components.time_date.const import CONF_DISPLAY_OPTIONS, DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.typing import WebSocketGenerator

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the forms."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"display_options": "time"},
    )
    await menuai.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 1
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_does_not_allow_beat(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test we get the forms."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with pytest.raises(vol.Invalid):
        await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"display_options": ["beat"]},
        )


async def test_single_instance(menuai: menuai) -> None:
    """Test we get the forms."""

    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options={CONF_DISPLAY_OPTIONS: "time"}
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"display_options": "time"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_timezone_not_set(menuai: menuai) -> None:
    """Test time zone not set."""
    menuai.config.time_zone = None

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"display_options": "time"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "timezone_not_exist"}


async def test_config_flow_preview(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the config flow preview."""
    client = await menuai_ws_client(menuai)
    freezer.move_to("2024-01-02 20:14:11.672")

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None
    assert result["preview"] == "time_date"

    await client.send_json_auto_id(
        {
            "type": "time_date/start_preview",
            "flow_id": result["flow_id"],
            "flow_type": "config_flow",
            "user_input": {"display_options": "time"},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] is None

    msg = await client.receive_json()
    assert msg["event"] == {
        "attributes": {"friendly_name": "Time", "icon": "mdi:clock"},
        "state": "12:14",
    }

    freezer.tick(60)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    msg = await client.receive_json()
    assert msg["event"] == {
        "attributes": {"friendly_name": "Time", "icon": "mdi:clock"},
        "state": "12:15",
    }
    assert len(menuai.states.async_all()) == 0
