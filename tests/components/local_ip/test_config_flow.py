"""Tests for the local_ip config_flow."""

from __future__ import annotations

from menuai.components.local_ip.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_config_flow(menuai: menuai) -> None:
    """Test we can finish a config flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY

    await menuai.async_block_till_done()
    state = menuai.states.get(f"sensor.{DOMAIN}")
    assert state


async def test_already_setup(menuai: menuai) -> None:
    """Test we abort if already setup."""
    MockConfigEntry(
        domain=DOMAIN,
        data={},
    ).add_to_menuai(menuai)

    # Should fail, same NAME
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
