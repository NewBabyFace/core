"""The tests for the Group Binary Sensor platform."""

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.components.group import DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component


async def test_default_state(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test binary_sensor group default state."""
    menuai.states.async_set("binary_sensor.kitchen", "on")
    menuai.states.async_set("binary_sensor.bedroom", "on")
    await async_setup_component(
        menuai,
        BINARY_SENSOR_DOMAIN,
        {
            BINARY_SENSOR_DOMAIN: {
                "platform": DOMAIN,
                "entities": ["binary_sensor.kitchen", "binary_sensor.bedroom"],
                "name": "Bedroom Group",
                "unique_id": "unique_identifier",
                "device_class": "presence",
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.bedroom_group")
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ENTITY_ID) == [
        "binary_sensor.kitchen",
        "binary_sensor.bedroom",
    ]

    entry = entity_registry.async_get("binary_sensor.bedroom_group")
    assert entry
    assert entry.unique_id == "unique_identifier"
    assert entry.original_name == "Bedroom Group"
    assert entry.original_device_class == "presence"


async def test_state_reporting_all(menuai: menuai) -> None:
    """Test the state reporting in 'all' mode.

    The group state is unavailable if all group members are unavailable.
    Otherwise, the group state is unknown if at least one group member is unknown or unavailable.
    Otherwise, the group state is off if at least one group member is off.
    Otherwise, the group state is on.
    """
    await async_setup_component(
        menuai,
        BINARY_SENSOR_DOMAIN,
        {
            BINARY_SENSOR_DOMAIN: {
                "platform": DOMAIN,
                "entities": ["binary_sensor.test1", "binary_sensor.test2"],
                "name": "Binary Sensor Group",
                "device_class": "presence",
                "all": "true",
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    # Initial state with no group member in the state machine -> unavailable
    assert (
        menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNAVAILABLE
    )

    # All group members unavailable -> unavailable
    menuai.states.async_set("binary_sensor.test1", STATE_UNAVAILABLE)
    menuai.states.async_set("binary_sensor.test2", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    assert (
        menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNAVAILABLE
    )

    # At least one member unknown or unavailable -> group unknown
    menuai.states.async_set("binary_sensor.test1", STATE_ON)
    menuai.states.async_set("binary_sensor.test2", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNKNOWN

    menuai.states.async_set("binary_sensor.test1", STATE_ON)
    menuai.states.async_set("binary_sensor.test2", STATE_UNKNOWN)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNKNOWN

    menuai.states.async_set("binary_sensor.test1", STATE_UNKNOWN)
    menuai.states.async_set("binary_sensor.test2", STATE_UNKNOWN)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNKNOWN

    menuai.states.async_set("binary_sensor.test1", STATE_OFF)
    menuai.states.async_set("binary_sensor.test2", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNKNOWN

    menuai.states.async_set("binary_sensor.test1", STATE_OFF)
    menuai.states.async_set("binary_sensor.test2", STATE_UNKNOWN)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNKNOWN

    menuai.states.async_set("binary_sensor.test1", STATE_UNKNOWN)
    menuai.states.async_set("binary_sensor.test2", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNKNOWN

    # At least one member off -> group off
    menuai.states.async_set("binary_sensor.test1", STATE_ON)
    menuai.states.async_set("binary_sensor.test2", STATE_OFF)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_OFF

    menuai.states.async_set("binary_sensor.test1", STATE_OFF)
    menuai.states.async_set("binary_sensor.test2", STATE_OFF)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_OFF

    # Otherwise -> on
    menuai.states.async_set("binary_sensor.test1", STATE_ON)
    menuai.states.async_set("binary_sensor.test2", STATE_ON)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_ON

    # All group members removed from the state machine -> unavailable
    menuai.states.async_remove("binary_sensor.test1")
    menuai.states.async_remove("binary_sensor.test2")
    await menuai.async_block_till_done()
    assert (
        menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNAVAILABLE
    )


async def test_state_reporting_any(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test the state reporting in 'any' mode.

    The group state is unavailable if all group members are unavailable.
    Otherwise, the group state is unknown if all group members are unknown.
    Otherwise, the group state is on if at least one group member is on.
    Otherwise, the group state is off.
    """
    await async_setup_component(
        menuai,
        BINARY_SENSOR_DOMAIN,
        {
            BINARY_SENSOR_DOMAIN: {
                "platform": DOMAIN,
                "entities": ["binary_sensor.test1", "binary_sensor.test2"],
                "name": "Binary Sensor Group",
                "device_class": "presence",
                "all": "false",
                "unique_id": "unique_identifier",
            }
        },
    )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    entry = entity_registry.async_get("binary_sensor.binary_sensor_group")
    assert entry
    assert entry.unique_id == "unique_identifier"

    # Initial state with no group member in the state machine -> unavailable
    assert (
        menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNAVAILABLE
    )

    # All group members unavailable -> unavailable
    menuai.states.async_set("binary_sensor.test1", STATE_UNAVAILABLE)
    menuai.states.async_set("binary_sensor.test2", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    assert (
        menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNAVAILABLE
    )

    # All group members unknown -> unknown
    menuai.states.async_set("binary_sensor.test1", STATE_UNKNOWN)
    menuai.states.async_set("binary_sensor.test2", STATE_UNKNOWN)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNKNOWN

    # Group members unknown or unavailable -> unknown
    menuai.states.async_set("binary_sensor.test1", STATE_UNKNOWN)
    menuai.states.async_set("binary_sensor.test2", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNKNOWN

    # At least one member on -> group on
    menuai.states.async_set("binary_sensor.test1", STATE_ON)
    menuai.states.async_set("binary_sensor.test2", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_ON

    menuai.states.async_set("binary_sensor.test1", STATE_ON)
    menuai.states.async_set("binary_sensor.test2", STATE_OFF)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_ON

    menuai.states.async_set("binary_sensor.test1", STATE_ON)
    menuai.states.async_set("binary_sensor.test2", STATE_ON)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_ON

    menuai.states.async_set("binary_sensor.test1", STATE_ON)
    menuai.states.async_set("binary_sensor.test2", STATE_UNKNOWN)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_ON

    # Otherwise -> off
    menuai.states.async_set("binary_sensor.test1", STATE_OFF)
    menuai.states.async_set("binary_sensor.test2", STATE_OFF)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_OFF

    menuai.states.async_set("binary_sensor.test1", STATE_UNKNOWN)
    menuai.states.async_set("binary_sensor.test2", STATE_OFF)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_OFF

    menuai.states.async_set("binary_sensor.test1", STATE_UNAVAILABLE)
    menuai.states.async_set("binary_sensor.test2", STATE_OFF)
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_OFF

    # All group members removed from the state machine -> unavailable
    menuai.states.async_remove("binary_sensor.test1")
    menuai.states.async_remove("binary_sensor.test2")
    await menuai.async_block_till_done()
    assert (
        menuai.states.get("binary_sensor.binary_sensor_group").state == STATE_UNAVAILABLE
    )
