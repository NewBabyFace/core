"""Test the Switch as X config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from menuai import config_entries
from menuai.components.switch_as_x.config_flow import SwitchAsXConfigFlowHandler
from menuai.components.switch_as_x.const import (
    CONF_INVERT,
    CONF_TARGET_DOMAIN,
    DOMAIN,
)
from menuai.const import CONF_ENTITY_ID, STATE_ON, Platform
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import entity_registry as er

from . import PLATFORMS_TO_TEST, STATE_MAP

from tests.common import MockConfigEntry, get_schema_suggested_value


@pytest.mark.parametrize("target_domain", PLATFORMS_TO_TEST)
async def test_config_flow(
    menuai: menuai,
    target_domain: Platform,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the config flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ENTITY_ID: "switch.ceiling",
            CONF_INVERT: False,
            CONF_TARGET_DOMAIN: target_domain,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ceiling"
    assert result["data"] == {}
    assert result["options"] == {
        CONF_ENTITY_ID: "switch.ceiling",
        CONF_INVERT: False,
        CONF_TARGET_DOMAIN: target_domain,
    }
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {
        CONF_ENTITY_ID: "switch.ceiling",
        CONF_INVERT: False,
        CONF_TARGET_DOMAIN: target_domain,
    }


@pytest.mark.parametrize(
    ("hidden_by_before", "hidden_by_after"),
    [
        (er.RegistryEntryHider.USER, er.RegistryEntryHider.USER),
        (None, er.RegistryEntryHider.INTEGRATION),
    ],
)
@pytest.mark.parametrize("target_domain", PLATFORMS_TO_TEST)
async def test_config_flow_registered_entity(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    target_domain: Platform,
    mock_setup_entry: AsyncMock,
    hidden_by_before: er.RegistryEntryHider | None,
    hidden_by_after: er.RegistryEntryHider,
) -> None:
    """Test the config flow hides a registered entity."""
    switch_entity_entry = entity_registry.async_get_or_create(
        "switch", "test", "unique", suggested_object_id="ceiling"
    )
    assert switch_entity_entry.entity_id == "switch.ceiling"
    entity_registry.async_update_entity("switch.ceiling", hidden_by=hidden_by_before)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ENTITY_ID: "switch.ceiling",
            CONF_INVERT: False,
            CONF_TARGET_DOMAIN: target_domain,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ceiling"
    assert result["data"] == {}
    assert result["options"] == {
        CONF_ENTITY_ID: "switch.ceiling",
        CONF_INVERT: False,
        CONF_TARGET_DOMAIN: target_domain,
    }
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {
        CONF_ENTITY_ID: "switch.ceiling",
        CONF_INVERT: False,
        CONF_TARGET_DOMAIN: target_domain,
    }

    switch_entity_entry = entity_registry.async_get("switch.ceiling")
    assert switch_entity_entry.hidden_by == hidden_by_after


@pytest.mark.parametrize("target_domain", PLATFORMS_TO_TEST)
async def test_options(
    menuai: menuai,
    target_domain: Platform,
) -> None:
    """Test reconfiguring."""
    switch_state = STATE_ON
    menuai.states.async_set("switch.ceiling", switch_state)
    switch_as_x_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_ENTITY_ID: "switch.ceiling",
            CONF_INVERT: True,
            CONF_TARGET_DOMAIN: target_domain,
        },
        title="ABC",
        version=SwitchAsXConfigFlowHandler.VERSION,
        minor_version=SwitchAsXConfigFlowHandler.MINOR_VERSION,
    )
    switch_as_x_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(switch_as_x_config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get(f"{target_domain}.abc")
    assert state.state == STATE_MAP[True][target_domain][switch_state]

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert config_entry

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert get_schema_suggested_value(result["data_schema"].schema, CONF_INVERT) is True

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_INVERT: False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_ENTITY_ID: "switch.ceiling",
        CONF_INVERT: False,
        CONF_TARGET_DOMAIN: target_domain,
    }
    assert config_entry.data == {}
    assert config_entry.options == {
        CONF_ENTITY_ID: "switch.ceiling",
        CONF_INVERT: False,
        CONF_TARGET_DOMAIN: target_domain,
    }
    assert config_entry.title == "ABC"

    # Check config entry is reloaded with new options
    await menuai.async_block_till_done()

    # Check the entity was updated, no new entity was created
    assert len(menuai.states.async_all()) == 2

    # Check the state of the entity has changed as expected
    state = menuai.states.get(f"{target_domain}.abc")
    assert state.state == STATE_MAP[False][target_domain][switch_state]
