"""The tests for the Modbus cover component."""

from pymodbus.exceptions import ModbusException
import pytest

from menuai.components.cover import DOMAIN as COVER_DOMAIN, CoverState
from menuai.components.menuai import SERVICE_UPDATE_ENTITY
from menuai.components.modbus.const import (
    CALL_TYPE_COIL,
    CALL_TYPE_REGISTER_HOLDING,
    CONF_DEVICE_ADDRESS,
    CONF_INPUT_TYPE,
    CONF_STATE_CLOSED,
    CONF_STATE_CLOSING,
    CONF_STATE_OPEN,
    CONF_STATE_OPENING,
    CONF_STATUS_REGISTER,
    CONF_STATUS_REGISTER_TYPE,
    MODBUS_DOMAIN,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    CONF_ADDRESS,
    CONF_COVERS,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    STATE_UNAVAILABLE,
)
from menuai.core import DOMAIN as menuai_DOMAIN, menuai, State
from menuai.setup import async_setup_component

from .conftest import TEST_ENTITY_NAME, ReadResult

ENTITY_ID = f"{COVER_DOMAIN}.{TEST_ENTITY_NAME}".replace(" ", "_")
ENTITY_ID2 = f"{ENTITY_ID}_2"


@pytest.mark.parametrize(
    "do_config",
    [
        {
            CONF_COVERS: [
                {
                    CONF_NAME: TEST_ENTITY_NAME,
                    CONF_ADDRESS: 1234,
                    CONF_INPUT_TYPE: CALL_TYPE_COIL,
                }
            ]
        },
        {
            CONF_COVERS: [
                {
                    CONF_NAME: TEST_ENTITY_NAME,
                    CONF_ADDRESS: 1234,
                    CONF_INPUT_TYPE: CALL_TYPE_REGISTER_HOLDING,
                    CONF_SLAVE: 10,
                    CONF_SCAN_INTERVAL: 20,
                }
            ]
        },
        {
            CONF_COVERS: [
                {
                    CONF_NAME: TEST_ENTITY_NAME,
                    CONF_ADDRESS: 1234,
                    CONF_INPUT_TYPE: CALL_TYPE_REGISTER_HOLDING,
                    CONF_DEVICE_ADDRESS: 10,
                    CONF_SCAN_INTERVAL: 20,
                }
            ]
        },
    ],
)
async def test_config_cover(menuai: menuai, mock_modbus) -> None:
    """Run configuration test for cover."""
    assert COVER_DOMAIN in menuai.config.components


@pytest.mark.parametrize(
    "do_config",
    [
        {
            CONF_COVERS: [
                {
                    CONF_NAME: TEST_ENTITY_NAME,
                    CONF_INPUT_TYPE: CALL_TYPE_COIL,
                    CONF_ADDRESS: 1234,
                    CONF_SLAVE: 1,
                },
            ],
        },
    ],
)
@pytest.mark.parametrize(
    ("register_words", "expected"),
    [
        (
            [0x00],
            CoverState.CLOSED,
        ),
        (
            [0x80],
            CoverState.CLOSED,
        ),
        (
            [0xFE],
            CoverState.CLOSED,
        ),
        (
            [0xFF],
            CoverState.OPEN,
        ),
        (
            [0x01],
            CoverState.OPEN,
        ),
    ],
)
async def test_coil_cover(menuai: menuai, expected, mock_do_cycle) -> None:
    """Run test for given config."""
    assert menuai.states.get(ENTITY_ID).state == expected


@pytest.mark.parametrize(
    "do_config",
    [
        {
            CONF_COVERS: [
                {
                    CONF_NAME: TEST_ENTITY_NAME,
                    CONF_ADDRESS: 1234,
                    CONF_SLAVE: 1,
                },
            ],
        },
    ],
)
@pytest.mark.parametrize(
    ("register_words", "expected"),
    [
        (
            [0x00],
            CoverState.CLOSED,
        ),
        (
            [0x80],
            CoverState.OPEN,
        ),
        (
            [0xFE],
            CoverState.OPEN,
        ),
        (
            [0xFF],
            CoverState.OPEN,
        ),
        (
            [0x01],
            CoverState.OPEN,
        ),
    ],
)
async def test_register_cover(menuai: menuai, expected, mock_do_cycle) -> None:
    """Run test for given config."""
    assert menuai.states.get(ENTITY_ID).state == expected


@pytest.mark.parametrize(
    "do_config",
    [
        {
            CONF_COVERS: [
                {
                    CONF_NAME: TEST_ENTITY_NAME,
                    CONF_ADDRESS: 1234,
                    CONF_STATUS_REGISTER_TYPE: CALL_TYPE_REGISTER_HOLDING,
                }
            ]
        },
    ],
)
async def test_service_cover_update(menuai: menuai, mock_modbus_ha) -> None:
    """Run test for service menuai.update_entity."""
    await menuai.services.async_call(
        menuai_DOMAIN,
        "update_entity",
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    assert menuai.states.get(ENTITY_ID).state == CoverState.CLOSED
    mock_modbus_ha.read_holding_registers.return_value = ReadResult([0x01])
    await menuai.services.async_call(
        menuai_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    assert menuai.states.get(ENTITY_ID).state == CoverState.OPEN


@pytest.mark.parametrize(
    "mock_test_state",
    [
        (State(ENTITY_ID, CoverState.CLOSED),),
        (State(ENTITY_ID, CoverState.CLOSING),),
        (State(ENTITY_ID, CoverState.OPENING),),
        (State(ENTITY_ID, CoverState.OPEN),),
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    "do_config",
    [
        {
            CONF_COVERS: [
                {
                    CONF_NAME: TEST_ENTITY_NAME,
                    CONF_INPUT_TYPE: CALL_TYPE_COIL,
                    CONF_ADDRESS: 1234,
                    CONF_STATE_OPEN: 1,
                    CONF_STATE_CLOSED: 0,
                    CONF_STATE_OPENING: 2,
                    CONF_STATE_CLOSING: 3,
                    CONF_STATUS_REGISTER: 1234,
                    CONF_STATUS_REGISTER_TYPE: CALL_TYPE_REGISTER_HOLDING,
                    CONF_SCAN_INTERVAL: 0,
                }
            ]
        },
    ],
)
async def test_restore_state_cover(
    menuai: menuai, mock_test_state, mock_modbus
) -> None:
    """Run test for cover restore state."""
    test_state = mock_test_state[0].state
    assert menuai.states.get(ENTITY_ID).state == test_state


@pytest.mark.parametrize(
    "do_config",
    [
        {
            CONF_COVERS: [
                {
                    CONF_NAME: TEST_ENTITY_NAME,
                    CONF_ADDRESS: 1234,
                    CONF_STATUS_REGISTER_TYPE: CALL_TYPE_REGISTER_HOLDING,
                    CONF_SCAN_INTERVAL: 0,
                },
                {
                    CONF_NAME: f"{TEST_ENTITY_NAME} 2",
                    CONF_INPUT_TYPE: CALL_TYPE_COIL,
                    CONF_ADDRESS: 1235,
                    CONF_SCAN_INTERVAL: 0,
                },
            ]
        },
    ],
)
async def test_service_cover_move(menuai: menuai, mock_modbus_ha) -> None:
    """Run test for service menuai.update_entity."""

    mock_modbus_ha.read_holding_registers.return_value = ReadResult([0x01])
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    assert menuai.states.get(ENTITY_ID).state == CoverState.OPEN

    mock_modbus_ha.read_holding_registers.return_value = ReadResult([0x00])
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    assert menuai.states.get(ENTITY_ID).state == CoverState.CLOSED

    await mock_modbus_ha.reset()
    mock_modbus_ha.read_holding_registers.side_effect = ModbusException("fail write_")
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    assert mock_modbus_ha.read_holding_registers.called
    assert menuai.states.get(ENTITY_ID).state == STATE_UNAVAILABLE

    mock_modbus_ha.read_coils.side_effect = ModbusException("fail write_")
    await menuai.services.async_call(
        COVER_DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: ENTITY_ID2}, blocking=True
    )
    assert menuai.states.get(ENTITY_ID2).state == STATE_UNAVAILABLE


async def test_no_discovery_info_cover(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test setup without discovery info."""
    assert COVER_DOMAIN not in menuai.config.components
    assert await async_setup_component(
        menuai,
        COVER_DOMAIN,
        {COVER_DOMAIN: {CONF_PLATFORM: MODBUS_DOMAIN}},
    )
    await menuai.async_block_till_done()
    assert COVER_DOMAIN in menuai.config.components
