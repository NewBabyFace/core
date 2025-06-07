"""Tests for emulated_roku config flow."""

from menuai import config_entries
from menuai.components.emulated_roku import config_flow
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_flow_works(menuai: menuai) -> None:
    """Test that config flow works."""
    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={"name": "Emulated Roku Test", "listen_port": 8060},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Emulated Roku Test"
    assert result["data"] == {"name": "Emulated Roku Test", "listen_port": 8060}


async def test_flow_already_registered_entry(menuai: menuai) -> None:
    """Test that config flow doesn't allow existing names."""
    MockConfigEntry(
        domain="emulated_roku", data={"name": "Emulated Roku Test", "listen_port": 8062}
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={"name": "Emulated Roku Test", "listen_port": 8062},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
