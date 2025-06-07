"""Test the System Monitor config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

from menuai import config_entries
from menuai.components.systemmonitor.const import CONF_PROCESS, DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import device_registry as dr, entity_registry as er

from tests.common import MockConfigEntry


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {}

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_already_configured(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test abort when already configured."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=config_entries.SOURCE_USER,
        options={},
    )
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_add_and_remove_processes(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test adding and removing process sensors."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=config_entries.SOURCE_USER,
        data={},
        options={},
        entry_id="1",
    )
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PROCESS: ["systemd"],
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "binary_sensor": {
            CONF_PROCESS: ["systemd"],
        }
    }

    # Add another
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PROCESS: ["systemd", "octave-cli"],
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "binary_sensor": {
            CONF_PROCESS: ["systemd", "octave-cli"],
        },
    }

    assert (
        entity_registry.async_get("binary_sensor.system_monitor_process_systemd")
        is not None
    )
    assert (
        entity_registry.async_get("binary_sensor.system_monitor_process_octave_cli")
        is not None
    )

    # Remove one
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PROCESS: ["systemd"],
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "binary_sensor": {
            CONF_PROCESS: ["systemd"],
        },
    }

    # Remove last
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PROCESS: [],
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "binary_sensor": {CONF_PROCESS: []},
    }

    assert (
        entity_registry.async_get("binary_sensor.systemmonitor_process_systemd") is None
    )
    assert (
        entity_registry.async_get("binary_sensor.systemmonitor_process_octave_cli")
        is None
    )
