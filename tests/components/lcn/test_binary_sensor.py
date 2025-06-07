"""Test for the LCN binary sensor platform."""

from unittest.mock import patch

from pypck.inputs import ModStatusBinSensors, ModStatusKeyLocks, ModStatusVar
from pypck.lcn_addr import LcnAddr
from pypck.lcn_defs import Var, VarValue
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components import automation, script
from menuai.components.automation import automations_with_entity
from menuai.components.lcn import DOMAIN
from menuai.components.lcn.helpers import get_device_connection
from menuai.components.script import scripts_with_entity
from menuai.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, Platform
from menuai.core import menuai, ServiceCall
from menuai.helpers import entity_registry as er, issue_registry as ir
from menuai.setup import async_setup_component

from .conftest import MockConfigEntry, init_integration

from tests.common import snapshot_platform

BINARY_SENSOR_LOCKREGULATOR1 = "binary_sensor.testmodule_sensor_lockregulator1"
BINARY_SENSOR_SENSOR1 = "binary_sensor.testmodule_binary_sensor1"
BINARY_SENSOR_KEYLOCK = "binary_sensor.testmodule_sensor_keylock"


async def test_setup_lcn_binary_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the setup of binary sensor."""
    with patch("menuai.components.lcn.PLATFORMS", [Platform.BINARY_SENSOR]):
        await init_integration(menuai, entry)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_pushed_lock_setpoint_status_change(
    menuai: menuai,
    entry: MockConfigEntry,
) -> None:
    """Test the lock setpoint sensor changes its state on status received."""
    await init_integration(menuai, entry)

    device_connection = get_device_connection(menuai, (0, 7, False), entry)
    address = LcnAddr(0, 7, False)

    # push status lock setpoint
    inp = ModStatusVar(address, Var.R1VARSETPOINT, VarValue(0x8000))
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(BINARY_SENSOR_LOCKREGULATOR1)
    assert state is not None
    assert state.state == STATE_ON

    # push status unlock setpoint
    inp = ModStatusVar(address, Var.R1VARSETPOINT, VarValue(0x7FFF))
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(BINARY_SENSOR_LOCKREGULATOR1)
    assert state is not None
    assert state.state == STATE_OFF


async def test_pushed_binsensor_status_change(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test the binary port sensor changes its state on status received."""
    await init_integration(menuai, entry)

    device_connection = get_device_connection(menuai, (0, 7, False), entry)
    address = LcnAddr(0, 7, False)
    states = [False] * 8

    # push status binary port "off"
    inp = ModStatusBinSensors(address, states)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(BINARY_SENSOR_SENSOR1)
    assert state is not None
    assert state.state == STATE_OFF

    # push status binary port "on"
    states[0] = True
    inp = ModStatusBinSensors(address, states)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(BINARY_SENSOR_SENSOR1)
    assert state is not None
    assert state.state == STATE_ON


async def test_pushed_keylock_status_change(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test the keylock sensor changes its state on status received."""
    await init_integration(menuai, entry)

    device_connection = get_device_connection(menuai, (0, 7, False), entry)
    address = LcnAddr(0, 7, False)
    states = [[False] * 8 for i in range(4)]

    # push status keylock "off"
    inp = ModStatusKeyLocks(address, states)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(BINARY_SENSOR_KEYLOCK)
    assert state is not None
    assert state.state == STATE_OFF

    # push status keylock "on"
    states[0][4] = True
    inp = ModStatusKeyLocks(address, states)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(BINARY_SENSOR_KEYLOCK)
    assert state is not None
    assert state.state == STATE_ON


async def test_unload_config_entry(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the binary sensor is removed when the config entry is unloaded."""
    await init_integration(menuai, entry)

    await menuai.config_entries.async_unload(entry.entry_id)
    assert menuai.states.get(BINARY_SENSOR_LOCKREGULATOR1).state == STATE_UNAVAILABLE
    assert menuai.states.get(BINARY_SENSOR_SENSOR1).state == STATE_UNAVAILABLE
    assert menuai.states.get(BINARY_SENSOR_KEYLOCK).state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    "entity_id",
    [
        "binary_sensor.testmodule_sensor_lockregulator1",
        "binary_sensor.testmodule_sensor_keylock",
    ],
)
async def test_create_issue(
    menuai: menuai,
    service_calls: list[ServiceCall],
    issue_registry: ir.IssueRegistry,
    entry: MockConfigEntry,
    entity_id,
) -> None:
    """Test we create an issue when an automation or script is using a deprecated entity."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "test",
                "trigger": {"platform": "state", "entity_id": entity_id},
                "action": {"action": "test.automation"},
            }
        },
    )

    assert await async_setup_component(
        menuai,
        script.DOMAIN,
        {
            script.DOMAIN: {
                "test": {
                    "sequence": {
                        "condition": "state",
                        "entity_id": entity_id,
                        "state": STATE_ON,
                    }
                }
            }
        },
    )

    await init_integration(menuai, entry)

    assert automations_with_entity(menuai, entity_id)[0] == "automation.test"
    assert scripts_with_entity(menuai, entity_id)[0] == "script.test"

    assert issue_registry.async_get_issue(
        DOMAIN, f"deprecated_binary_sensor_{entity_id}"
    )
