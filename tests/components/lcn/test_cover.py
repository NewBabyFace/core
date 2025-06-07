"""Test for the LCN cover platform."""

from unittest.mock import patch

from pypck.inputs import (
    ModStatusMotorPositionBS4,
    ModStatusMotorPositionModule,
    ModStatusOutput,
    ModStatusRelays,
)
from pypck.lcn_addr import LcnAddr
from pypck.lcn_defs import MotorPositioningMode, MotorReverseTime, MotorStateModifier
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as DOMAIN_COVER,
    CoverState,
)
from menuai.components.lcn.helpers import get_device_connection
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
    STATE_UNAVAILABLE,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import MockConfigEntry, MockModuleConnection, init_integration

from tests.common import snapshot_platform

COVER_OUTPUTS = "cover.testmodule_cover_outputs"
COVER_RELAYS = "cover.testmodule_cover_relays"
COVER_RELAYS_BS4 = "cover.testmodule_cover_relays_bs4"
COVER_RELAYS_MODULE = "cover.testmodule_cover_relays_module"


async def test_setup_lcn_cover(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the setup of cover."""
    with patch("menuai.components.lcn.PLATFORMS", [Platform.COVER]):
        await init_integration(menuai, entry)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_outputs_open(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the outputs cover opens."""
    await init_integration(menuai, entry)

    with patch.object(
        MockModuleConnection, "control_motor_outputs"
    ) as control_motor_outputs:
        state = menuai.states.get(COVER_OUTPUTS)
        state.state = CoverState.CLOSED

        # command failed
        control_motor_outputs.return_value = False

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: COVER_OUTPUTS},
            blocking=True,
        )

        control_motor_outputs.assert_awaited_with(
            MotorStateModifier.UP, MotorReverseTime.RT1200
        )

        state = menuai.states.get(COVER_OUTPUTS)
        assert state is not None
        assert state.state != CoverState.OPENING

        # command success
        control_motor_outputs.reset_mock(return_value=True)
        control_motor_outputs.return_value = True

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: COVER_OUTPUTS},
            blocking=True,
        )

        control_motor_outputs.assert_awaited_with(
            MotorStateModifier.UP, MotorReverseTime.RT1200
        )

        state = menuai.states.get(COVER_OUTPUTS)
        assert state is not None
        assert state.state == CoverState.OPENING


async def test_outputs_close(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the outputs cover closes."""
    await init_integration(menuai, entry)

    with patch.object(
        MockModuleConnection, "control_motor_outputs"
    ) as control_motor_outputs:
        state = menuai.states.get(COVER_OUTPUTS)
        state.state = CoverState.OPEN

        # command failed
        control_motor_outputs.return_value = False

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: COVER_OUTPUTS},
            blocking=True,
        )

        control_motor_outputs.assert_awaited_with(
            MotorStateModifier.DOWN, MotorReverseTime.RT1200
        )

        state = menuai.states.get(COVER_OUTPUTS)
        assert state is not None
        assert state.state != CoverState.CLOSING

        # command success
        control_motor_outputs.reset_mock(return_value=True)
        control_motor_outputs.return_value = True

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: COVER_OUTPUTS},
            blocking=True,
        )

        control_motor_outputs.assert_awaited_with(
            MotorStateModifier.DOWN, MotorReverseTime.RT1200
        )

        state = menuai.states.get(COVER_OUTPUTS)
        assert state is not None
        assert state.state == CoverState.CLOSING


async def test_outputs_stop(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the outputs cover stops."""
    await init_integration(menuai, entry)

    with patch.object(
        MockModuleConnection, "control_motor_outputs"
    ) as control_motor_outputs:
        state = menuai.states.get(COVER_OUTPUTS)
        state.state = CoverState.CLOSING

        # command failed
        control_motor_outputs.return_value = False

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_STOP_COVER,
            {ATTR_ENTITY_ID: COVER_OUTPUTS},
            blocking=True,
        )

        control_motor_outputs.assert_awaited_with(MotorStateModifier.STOP)

        state = menuai.states.get(COVER_OUTPUTS)
        assert state is not None
        assert state.state == CoverState.CLOSING

        # command success
        control_motor_outputs.reset_mock(return_value=True)
        control_motor_outputs.return_value = True

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_STOP_COVER,
            {ATTR_ENTITY_ID: COVER_OUTPUTS},
            blocking=True,
        )

        control_motor_outputs.assert_awaited_with(MotorStateModifier.STOP)

        state = menuai.states.get(COVER_OUTPUTS)
        assert state is not None
        assert state.state not in (CoverState.CLOSING, CoverState.OPENING)


async def test_relays_open(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the relays cover opens."""
    await init_integration(menuai, entry)

    with patch.object(
        MockModuleConnection, "control_motor_relays"
    ) as control_motor_relays:
        state = menuai.states.get(COVER_RELAYS)
        state.state = CoverState.CLOSED

        # command failed
        control_motor_relays.return_value = False

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: COVER_RELAYS},
            blocking=True,
        )

        control_motor_relays.assert_awaited_with(
            0, MotorStateModifier.UP, MotorPositioningMode.NONE
        )

        state = menuai.states.get(COVER_RELAYS)
        assert state is not None
        assert state.state != CoverState.OPENING

        # command success
        control_motor_relays.reset_mock(return_value=True)
        control_motor_relays.return_value = True

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: COVER_RELAYS},
            blocking=True,
        )

        control_motor_relays.assert_awaited_with(
            0, MotorStateModifier.UP, MotorPositioningMode.NONE
        )

        state = menuai.states.get(COVER_RELAYS)
        assert state is not None
        assert state.state == CoverState.OPENING


async def test_relays_close(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the relays cover closes."""
    await init_integration(menuai, entry)

    with patch.object(
        MockModuleConnection, "control_motor_relays"
    ) as control_motor_relays:
        state = menuai.states.get(COVER_RELAYS)
        state.state = CoverState.OPEN

        # command failed
        control_motor_relays.return_value = False

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: COVER_RELAYS},
            blocking=True,
        )

        control_motor_relays.assert_awaited_with(
            0, MotorStateModifier.DOWN, MotorPositioningMode.NONE
        )

        state = menuai.states.get(COVER_RELAYS)
        assert state is not None
        assert state.state != CoverState.CLOSING

        # command success
        control_motor_relays.reset_mock(return_value=True)
        control_motor_relays.return_value = True

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: COVER_RELAYS},
            blocking=True,
        )

        control_motor_relays.assert_awaited_with(
            0, MotorStateModifier.DOWN, MotorPositioningMode.NONE
        )

        state = menuai.states.get(COVER_RELAYS)
        assert state is not None
        assert state.state == CoverState.CLOSING


async def test_relays_stop(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the relays cover stops."""
    await init_integration(menuai, entry)

    with patch.object(
        MockModuleConnection, "control_motor_relays"
    ) as control_motor_relays:
        state = menuai.states.get(COVER_RELAYS)
        state.state = CoverState.CLOSING

        # command failed
        control_motor_relays.return_value = False

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_STOP_COVER,
            {ATTR_ENTITY_ID: COVER_RELAYS},
            blocking=True,
        )

        control_motor_relays.assert_awaited_with(
            0, MotorStateModifier.STOP, MotorPositioningMode.NONE
        )

        state = menuai.states.get(COVER_RELAYS)
        assert state is not None
        assert state.state == CoverState.CLOSING

        # command success
        control_motor_relays.reset_mock(return_value=True)
        control_motor_relays.return_value = True

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_STOP_COVER,
            {ATTR_ENTITY_ID: COVER_RELAYS},
            blocking=True,
        )

        control_motor_relays.assert_awaited_with(
            0, MotorStateModifier.STOP, MotorPositioningMode.NONE
        )

        state = menuai.states.get(COVER_RELAYS)
        assert state is not None
        assert state.state not in (CoverState.CLOSING, CoverState.OPENING)


@pytest.mark.parametrize(
    ("entity_id", "motor", "positioning_mode"),
    [
        (COVER_RELAYS_BS4, 1, MotorPositioningMode.BS4),
        (COVER_RELAYS_MODULE, 2, MotorPositioningMode.MODULE),
    ],
)
async def test_relays_set_position(
    menuai: menuai,
    entry: MockConfigEntry,
    entity_id: str,
    motor: int,
    positioning_mode: MotorPositioningMode,
) -> None:
    """Test the relays cover moves to position."""
    await init_integration(menuai, entry)

    with patch.object(
        MockModuleConnection, "control_motor_relays_position"
    ) as control_motor_relays_position:
        state = menuai.states.get(entity_id)
        state.state = CoverState.CLOSED

        # command failed
        control_motor_relays_position.return_value = False

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_SET_COVER_POSITION,
            {ATTR_ENTITY_ID: entity_id, ATTR_POSITION: 50},
            blocking=True,
        )

        control_motor_relays_position.assert_awaited_with(
            motor, 50, mode=positioning_mode
        )

        state = menuai.states.get(entity_id)
        assert state.state == CoverState.CLOSED

        # command success
        control_motor_relays_position.reset_mock(return_value=True)
        control_motor_relays_position.return_value = True

        await menuai.services.async_call(
            DOMAIN_COVER,
            SERVICE_SET_COVER_POSITION,
            {ATTR_ENTITY_ID: entity_id, ATTR_POSITION: 50},
            blocking=True,
        )

        control_motor_relays_position.assert_awaited_with(
            motor, 50, mode=positioning_mode
        )

        state = menuai.states.get(entity_id)
        assert state.state == CoverState.OPEN


async def test_pushed_outputs_status_change(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test the outputs cover changes its state on status received."""
    await init_integration(menuai, entry)

    device_connection = get_device_connection(menuai, (0, 7, False), entry)
    address = LcnAddr(0, 7, False)

    state = menuai.states.get(COVER_OUTPUTS)
    state.state = CoverState.CLOSED

    # push status "open"
    inp = ModStatusOutput(address, 0, 100)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_OUTPUTS)
    assert state is not None
    assert state.state == CoverState.OPENING

    # push status "stop"
    inp = ModStatusOutput(address, 0, 0)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_OUTPUTS)
    assert state is not None
    assert state.state not in (CoverState.OPENING, CoverState.CLOSING)

    # push status "close"
    inp = ModStatusOutput(address, 1, 100)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_OUTPUTS)
    assert state is not None
    assert state.state == CoverState.CLOSING


async def test_pushed_relays_status_change(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test the relays cover changes its state on status received."""
    await init_integration(menuai, entry)

    device_connection = get_device_connection(menuai, (0, 7, False), entry)
    address = LcnAddr(0, 7, False)
    states = [False] * 8

    for entity_id in (COVER_RELAYS, COVER_RELAYS_BS4, COVER_RELAYS_MODULE):
        state = menuai.states.get(entity_id)
        state.state = CoverState.CLOSED

    # push status "open"
    states[0:2] = [True, False]
    inp = ModStatusRelays(address, states)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_RELAYS)
    assert state is not None
    assert state.state == CoverState.OPENING

    # push status "stop"
    states[0] = False
    inp = ModStatusRelays(address, states)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_RELAYS)
    assert state is not None
    assert state.state not in (CoverState.OPENING, CoverState.CLOSING)

    # push status "close"
    states[0:2] = [True, True]
    inp = ModStatusRelays(address, states)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_RELAYS)
    assert state is not None
    assert state.state == CoverState.CLOSING

    # push status "set position" via BS4
    inp = ModStatusMotorPositionBS4(address, 1, 50)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_RELAYS_BS4)
    assert state is not None
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 50

    # push status "set position" via MODULE
    inp = ModStatusMotorPositionModule(address, 2, 75)
    await device_connection.async_process_input(inp)
    await menuai.async_block_till_done()

    state = menuai.states.get(COVER_RELAYS_MODULE)
    assert state is not None
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 75


async def test_unload_config_entry(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test the cover is removed when the config entry is unloaded."""
    await init_integration(menuai, entry)

    await menuai.config_entries.async_unload(entry.entry_id)
    assert menuai.states.get(COVER_OUTPUTS).state == STATE_UNAVAILABLE
    assert menuai.states.get(COVER_RELAYS).state == STATE_UNAVAILABLE
