"""Test for the LCN sensor platform."""

from unittest.mock import patch

from pypck.inputs import ModStatusLedsAndLogicOps, ModStatusVar
from pypck.lcn_addr import LcnAddr
from pypck.lcn_defs import LedStatus, LogicOpStatus, Var, VarValue
from syrupy.assertion import SnapshotAssertion

from menuai.components.lcn.helpers import get_device_connection
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import MockConfigEntry, init_integration

from tests.common import snapshot_platform

SENSOR_VAR1 = "sensor.testmodule_sensor_var1"
SENSOR_SETPOINT1 = "sensor.testmodule_sensor_setpoint1"
SENSOR_LED6 = "sensor.testmodule_sensor_led6"
SENSOR_LOGICOP1 = "sensor.testmodule_sensor_logicop1"


async def test_setup_lcn_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the setup of sensor."""
    with patch("menuai.components.lcn.PLATFORMS", [Platform.SENSOR]):
        await init_integration(menuai, entry)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_pushed_variable_status_change(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test the variable sensor changes its state on status received."""
    await init_integration(menuai, entry)

    device_connection = get_device_connection(menuai, (0, 7, False), entry)
    address = LcnAddr(0, 7, False)

    # push status variable
    inp = ModStatusVar(address, Var.VAR1, VarValue.from_celsius(42))
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(SENSOR_VAR1)
    assert state is not None
    assert float(state.state) == 42.0

    # push status setpoint
    inp = ModStatusVar(address, Var.R1VARSETPOINT, VarValue.from_celsius(42))
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(SENSOR_SETPOINT1)
    assert state is not None
    assert float(state.state) == 42.0


async def test_pushed_ledlogicop_status_change(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test the led and logicop sensor changes its state on status received."""
    await init_integration(menuai, entry)

    device_connection = get_device_connection(menuai, (0, 7, False), entry)
    address = LcnAddr(0, 7, False)

    states_led = [LedStatus.OFF] * 12
    states_logicop = [LogicOpStatus.NONE] * 4

    states_led[5] = LedStatus.ON
    states_logicop[0] = LogicOpStatus.ALL

    # push status led and logicop
    inp = ModStatusLedsAndLogicOps(address, states_led, states_logicop)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(SENSOR_LED6)
    assert state is not None
    assert state.state == "on"

    state = menuai.states.get(SENSOR_LOGICOP1)
    assert state is not None
    assert state.state == "all"


async def test_unload_config_entry(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the sensor is removed when the config entry is unloaded."""
    await init_integration(menuai, entry)

    await menuai.config_entries.async_unload(entry.entry_id)
    assert menuai.states.get(SENSOR_VAR1).state == STATE_UNAVAILABLE
    assert menuai.states.get(SENSOR_SETPOINT1).state == STATE_UNAVAILABLE
    assert menuai.states.get(SENSOR_LED6).state == STATE_UNAVAILABLE
    assert menuai.states.get(SENSOR_LOGICOP1).state == STATE_UNAVAILABLE
