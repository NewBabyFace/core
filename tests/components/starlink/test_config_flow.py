"""Test the Starlink config flow."""

from menuai import config_entries
from menuai.components.starlink.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_IP_ADDRESS
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .patchers import DEVICE_FOUND_PATCHER, NO_DEVICE_PATCHER, SETUP_ENTRY_PATCHER

from tests.common import MockConfigEntry


async def test_flow_user_fails_can_succeed(menuai: menuai) -> None:
    """Test user initialized flow can still succeed after failure when Starlink is available."""
    user_input = {CONF_IP_ADDRESS: "192.168.100.1:9200"}

    with NO_DEVICE_PATCHER, SETUP_ENTRY_PATCHER:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )
        await menuai.async_block_till_done()
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=user_input,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]

    with DEVICE_FOUND_PATCHER, SETUP_ENTRY_PATCHER:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=user_input,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == user_input


async def test_flow_user_success(menuai: menuai) -> None:
    """Test user initialized flow succeeds when Starlink is available."""
    user_input = {CONF_IP_ADDRESS: "192.168.100.1:9200"}

    with DEVICE_FOUND_PATCHER, SETUP_ENTRY_PATCHER:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )
        await menuai.async_block_till_done()
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=user_input,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == user_input


async def test_flow_user_duplicate_abort(menuai: menuai) -> None:
    """Test user initialized flow aborts when Starlink is already configured."""
    user_input = {CONF_IP_ADDRESS: "192.168.100.1:9200"}

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=user_input,
        unique_id="some-valid-id",
        state=config_entries.ConfigEntryState.LOADED,
    )
    entry.add_to_menuai(menuai)

    with DEVICE_FOUND_PATCHER, SETUP_ENTRY_PATCHER:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )
        await menuai.async_block_till_done()
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=user_input,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
