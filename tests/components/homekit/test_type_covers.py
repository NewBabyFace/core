"""Test different accessory types: Covers."""

from menuai.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN as COVER_DOMAIN,
    CoverEntityFeature,
    CoverState,
)
from menuai.components.homekit.const import (
    ATTR_OBSTRUCTION_DETECTED,
    ATTR_VALUE,
    CONF_LINKED_OBSTRUCTION_SENSOR,
    HK_DOOR_CLOSED,
    HK_DOOR_CLOSING,
    HK_DOOR_OPEN,
    HK_DOOR_OPENING,
    PROP_MAX_VALUE,
    PROP_MIN_VALUE,
)
from menuai.components.homekit.type_covers import (
    Door,
    GarageDoorOpener,
    Window,
    WindowCovering,
    WindowCoveringBasic,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    EVENT_menuai_START,
    SERVICE_SET_COVER_TILT_POSITION,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from menuai.core import CoreState, Event, menuai
from menuai.helpers import entity_registry as er

from tests.common import async_mock_service


async def test_garage_door_open_close(
    menuai: menuai, hk_driver, events: list[Event]
) -> None:
    """Test if accessory and HA are updated accordingly."""
    entity_id = "cover.garage_door"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = GarageDoorOpener(menuai, hk_driver, "Garage Door", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 4  # GarageDoorOpener

    assert acc.char_current_state.value == HK_DOOR_OPEN
    assert acc.char_target_state.value == HK_DOOR_OPEN

    menuai.states.async_set(
        entity_id, CoverState.CLOSED, {ATTR_OBSTRUCTION_DETECTED: False}
    )
    await menuai.async_block_till_done()
    assert acc.char_current_state.value == HK_DOOR_CLOSED
    assert acc.char_target_state.value == HK_DOOR_CLOSED
    assert acc.char_obstruction_detected.value is False

    menuai.states.async_set(entity_id, CoverState.OPEN, {ATTR_OBSTRUCTION_DETECTED: True})
    await menuai.async_block_till_done()
    assert acc.char_current_state.value == HK_DOOR_OPEN
    assert acc.char_target_state.value == HK_DOOR_OPEN
    assert acc.char_obstruction_detected.value is True

    menuai.states.async_set(
        entity_id, STATE_UNAVAILABLE, {ATTR_OBSTRUCTION_DETECTED: True}
    )
    await menuai.async_block_till_done()
    assert acc.char_current_state.value == HK_DOOR_OPEN
    assert acc.char_target_state.value == HK_DOOR_OPEN
    assert acc.char_obstruction_detected.value is True
    assert acc.available is False

    menuai.states.async_set(entity_id, STATE_UNKNOWN)
    await menuai.async_block_till_done()
    assert acc.char_current_state.value == HK_DOOR_OPEN
    assert acc.char_target_state.value == HK_DOOR_OPEN
    assert acc.available is True

    # Set from HomeKit
    call_close_cover = async_mock_service(menuai, COVER_DOMAIN, "close_cover")
    call_open_cover = async_mock_service(menuai, COVER_DOMAIN, "open_cover")

    acc.char_target_state.client_update_value(1)
    await menuai.async_block_till_done()
    assert call_close_cover
    assert call_close_cover[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_current_state.value == HK_DOOR_CLOSING
    assert acc.char_target_state.value == HK_DOOR_CLOSED
    assert len(events) == 1
    assert events[-1].data[ATTR_VALUE] is None

    menuai.states.async_set(entity_id, CoverState.CLOSED)
    await menuai.async_block_till_done()

    acc.char_target_state.client_update_value(1)
    await menuai.async_block_till_done()
    assert acc.char_current_state.value == HK_DOOR_CLOSED
    assert acc.char_target_state.value == HK_DOOR_CLOSED
    assert len(events) == 2
    assert events[-1].data[ATTR_VALUE] is None

    acc.char_target_state.client_update_value(0)
    await menuai.async_block_till_done()
    assert call_open_cover
    assert call_open_cover[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_current_state.value == HK_DOOR_OPENING
    assert acc.char_target_state.value == HK_DOOR_OPEN
    assert len(events) == 3
    assert events[-1].data[ATTR_VALUE] is None

    menuai.states.async_set(entity_id, CoverState.OPEN)
    await menuai.async_block_till_done()

    acc.char_target_state.client_update_value(0)
    await menuai.async_block_till_done()
    assert acc.char_current_state.value == HK_DOOR_OPEN
    assert acc.char_target_state.value == HK_DOOR_OPEN
    assert len(events) == 4
    assert events[-1].data[ATTR_VALUE] is None


async def test_door_instantiate_set_position(menuai: menuai, hk_driver) -> None:
    """Test if Door accessory is instantiated correctly and can set position."""
    entity_id = "cover.door"

    menuai.states.async_set(
        entity_id,
        CoverState.OPEN,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: 0,
        },
    )
    await menuai.async_block_till_done()
    acc = Door(menuai, hk_driver, "Door", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 12  # Door

    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0

    menuai.states.async_set(
        entity_id,
        CoverState.OPEN,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: 50,
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 50
    assert acc.char_target_position.value == 50
    assert acc.char_position_state.value == 2

    menuai.states.async_set(
        entity_id,
        CoverState.OPEN,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: "GARBAGE",
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 50
    assert acc.char_target_position.value == 50
    assert acc.char_position_state.value == 2


async def test_windowcovering_set_cover_position(
    menuai: menuai, hk_driver, events: list[Event]
) -> None:
    """Test if accessory and HA are updated accordingly."""
    entity_id = "cover.window"

    menuai.states.async_set(
        entity_id,
        STATE_UNKNOWN,
        {ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION},
    )
    await menuai.async_block_till_done()
    acc = WindowCovering(menuai, hk_driver, "Cover", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 14  # WindowCovering

    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0

    menuai.states.async_set(
        entity_id,
        STATE_UNKNOWN,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: None,
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 2

    menuai.states.async_set(
        entity_id,
        CoverState.OPENING,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: 60,
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 60
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 1

    menuai.states.async_set(
        entity_id,
        CoverState.OPENING,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: 70.0,
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 70
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 1

    menuai.states.async_set(
        entity_id,
        CoverState.CLOSING,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: 50,
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 50
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 0

    menuai.states.async_set(
        entity_id,
        CoverState.OPEN,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: 50,
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 50
    assert acc.char_target_position.value == 50
    assert acc.char_position_state.value == 2

    # Set from HomeKit
    call_set_cover_position = async_mock_service(
        menuai, COVER_DOMAIN, "set_cover_position"
    )

    acc.char_target_position.client_update_value(25)
    await menuai.async_block_till_done()
    assert call_set_cover_position[0]
    assert call_set_cover_position[0].data[ATTR_ENTITY_ID] == entity_id
    assert call_set_cover_position[0].data[ATTR_POSITION] == 25
    assert acc.char_current_position.value == 50
    assert acc.char_target_position.value == 25
    assert len(events) == 1
    assert events[-1].data[ATTR_VALUE] == 25

    acc.char_target_position.client_update_value(75)
    await menuai.async_block_till_done()
    assert call_set_cover_position[1]
    assert call_set_cover_position[1].data[ATTR_ENTITY_ID] == entity_id
    assert call_set_cover_position[1].data[ATTR_POSITION] == 75
    assert acc.char_current_position.value == 50
    assert acc.char_target_position.value == 75
    assert len(events) == 2
    assert events[-1].data[ATTR_VALUE] == 75


async def test_window_instantiate_set_position(menuai: menuai, hk_driver) -> None:
    """Test if Window accessory is instantiated correctly and can set position."""
    entity_id = "cover.window"

    menuai.states.async_set(
        entity_id,
        CoverState.OPEN,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: 0,
        },
    )
    await menuai.async_block_till_done()
    acc = Window(menuai, hk_driver, "Window", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 13  # Window

    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0

    menuai.states.async_set(
        entity_id,
        CoverState.OPEN,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: 50,
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 50
    assert acc.char_target_position.value == 50
    assert acc.char_position_state.value == 2

    menuai.states.async_set(
        entity_id,
        CoverState.OPEN,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_POSITION,
            ATTR_CURRENT_POSITION: "GARBAGE",
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 50
    assert acc.char_target_position.value == 50
    assert acc.char_position_state.value == 2


async def test_windowcovering_cover_set_tilt(
    menuai: menuai, hk_driver, events: list[Event]
) -> None:
    """Test if accessory and HA update slat tilt accordingly."""
    entity_id = "cover.window"

    menuai.states.async_set(
        entity_id,
        STATE_UNKNOWN,
        {ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_TILT_POSITION},
    )
    await menuai.async_block_till_done()
    acc = WindowCovering(menuai, hk_driver, "Cover", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 14  # CATEGORY_WINDOW_COVERING

    assert acc.char_current_tilt.value == 0
    assert acc.char_target_tilt.value == 0

    menuai.states.async_set(
        entity_id, CoverState.CLOSING, {ATTR_CURRENT_TILT_POSITION: None}
    )
    await menuai.async_block_till_done()
    assert acc.char_current_tilt.value == 0
    assert acc.char_target_tilt.value == 0

    menuai.states.async_set(
        entity_id, CoverState.CLOSING, {ATTR_CURRENT_TILT_POSITION: 100}
    )
    await menuai.async_block_till_done()
    assert acc.char_current_tilt.value == 90
    assert acc.char_target_tilt.value == 90

    menuai.states.async_set(
        entity_id, CoverState.CLOSING, {ATTR_CURRENT_TILT_POSITION: 50}
    )
    await menuai.async_block_till_done()
    assert acc.char_current_tilt.value == 0
    assert acc.char_target_tilt.value == 0

    menuai.states.async_set(
        entity_id, CoverState.CLOSING, {ATTR_CURRENT_TILT_POSITION: 0}
    )
    await menuai.async_block_till_done()
    assert acc.char_current_tilt.value == -90
    assert acc.char_target_tilt.value == -90

    # set from HomeKit
    call_set_tilt_position = async_mock_service(
        menuai, COVER_DOMAIN, SERVICE_SET_COVER_TILT_POSITION
    )

    # HomeKit sets tilts between -90 and 90 (degrees), whereas
    # menuai expects a % between 0 and 100. Keep that in mind
    # when comparing
    acc.char_target_tilt.client_update_value(90)
    await menuai.async_block_till_done()
    assert call_set_tilt_position[0]
    assert call_set_tilt_position[0].data[ATTR_ENTITY_ID] == entity_id
    assert call_set_tilt_position[0].data[ATTR_TILT_POSITION] == 100
    assert acc.char_current_tilt.value == -90
    assert acc.char_target_tilt.value == 90
    assert len(events) == 1
    assert events[-1].data[ATTR_VALUE] == 100

    acc.char_target_tilt.client_update_value(45)
    await menuai.async_block_till_done()
    assert call_set_tilt_position[1]
    assert call_set_tilt_position[1].data[ATTR_ENTITY_ID] == entity_id
    assert call_set_tilt_position[1].data[ATTR_TILT_POSITION] == 75
    assert acc.char_current_tilt.value == -90
    assert acc.char_target_tilt.value == 45
    assert len(events) == 2
    assert events[-1].data[ATTR_VALUE] == 75


async def test_windowcovering_tilt_only(menuai: menuai, hk_driver) -> None:
    """Test we lock the window covering closed when its tilt only."""
    entity_id = "cover.window"

    menuai.states.async_set(
        entity_id,
        STATE_UNKNOWN,
        {ATTR_SUPPORTED_FEATURES: CoverEntityFeature.SET_TILT_POSITION},
    )
    await menuai.async_block_till_done()
    acc = WindowCovering(menuai, hk_driver, "Cover", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 14  # WindowCovering

    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0
    assert acc.char_target_position.properties[PROP_MIN_VALUE] == 0
    assert acc.char_target_position.properties[PROP_MAX_VALUE] == 0


async def test_windowcovering_open_close(
    menuai: menuai, hk_driver, events: list[Event]
) -> None:
    """Test if accessory and HA are updated accordingly."""
    entity_id = "cover.window"

    menuai.states.async_set(entity_id, STATE_UNKNOWN, {ATTR_SUPPORTED_FEATURES: 0})
    acc = WindowCoveringBasic(menuai, hk_driver, "Cover", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 14  # WindowCovering

    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 2

    menuai.states.async_set(entity_id, STATE_UNKNOWN)
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 2

    menuai.states.async_set(entity_id, CoverState.OPENING)
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 1

    menuai.states.async_set(entity_id, CoverState.OPEN)
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 100
    assert acc.char_target_position.value == 100
    assert acc.char_position_state.value == 2

    menuai.states.async_set(entity_id, CoverState.CLOSING)
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 100
    assert acc.char_target_position.value == 100
    assert acc.char_position_state.value == 0

    menuai.states.async_set(entity_id, CoverState.CLOSED)
    await menuai.async_block_till_done()
    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 2

    # Set from HomeKit
    call_close_cover = async_mock_service(menuai, COVER_DOMAIN, "close_cover")
    call_open_cover = async_mock_service(menuai, COVER_DOMAIN, "open_cover")

    acc.char_target_position.client_update_value(25)
    await menuai.async_block_till_done()
    assert call_close_cover
    assert call_close_cover[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 2
    assert len(events) == 1
    assert events[-1].data[ATTR_VALUE] is None

    acc.char_target_position.client_update_value(90)
    await menuai.async_block_till_done()
    assert call_open_cover[0]
    assert call_open_cover[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_current_position.value == 100
    assert acc.char_target_position.value == 100
    assert acc.char_position_state.value == 2
    assert len(events) == 2
    assert events[-1].data[ATTR_VALUE] is None

    acc.char_target_position.client_update_value(55)
    await menuai.async_block_till_done()
    assert call_open_cover[1]
    assert call_open_cover[1].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_current_position.value == 100
    assert acc.char_target_position.value == 100
    assert acc.char_position_state.value == 2
    assert len(events) == 3
    assert events[-1].data[ATTR_VALUE] is None


async def test_windowcovering_open_close_stop(
    menuai: menuai, hk_driver, events: list[Event]
) -> None:
    """Test if accessory and HA are updated accordingly."""
    entity_id = "cover.window"

    menuai.states.async_set(
        entity_id, STATE_UNKNOWN, {ATTR_SUPPORTED_FEATURES: CoverEntityFeature.STOP}
    )
    acc = WindowCoveringBasic(menuai, hk_driver, "Cover", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    # Set from HomeKit
    call_close_cover = async_mock_service(menuai, COVER_DOMAIN, "close_cover")
    call_open_cover = async_mock_service(menuai, COVER_DOMAIN, "open_cover")
    call_stop_cover = async_mock_service(menuai, COVER_DOMAIN, "stop_cover")

    acc.char_target_position.client_update_value(25)
    await menuai.async_block_till_done()
    assert call_close_cover
    assert call_close_cover[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_current_position.value == 0
    assert acc.char_target_position.value == 0
    assert acc.char_position_state.value == 2
    assert len(events) == 1
    assert events[-1].data[ATTR_VALUE] is None

    acc.char_target_position.client_update_value(90)
    await menuai.async_block_till_done()
    assert call_open_cover
    assert call_open_cover[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_current_position.value == 100
    assert acc.char_target_position.value == 100
    assert acc.char_position_state.value == 2
    assert len(events) == 2
    assert events[-1].data[ATTR_VALUE] is None

    acc.char_target_position.client_update_value(55)
    await menuai.async_block_till_done()
    assert call_stop_cover
    assert call_stop_cover[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_current_position.value == 50
    assert acc.char_target_position.value == 50
    assert acc.char_position_state.value == 2
    assert len(events) == 3
    assert events[-1].data[ATTR_VALUE] is None


async def test_windowcovering_open_close_with_position_and_stop(
    menuai: menuai, hk_driver, events: list[Event]
) -> None:
    """Test if accessory and HA are updated accordingly."""
    entity_id = "cover.stop_window"

    menuai.states.async_set(
        entity_id,
        STATE_UNKNOWN,
        {
            ATTR_SUPPORTED_FEATURES: CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        },
    )
    acc = WindowCovering(menuai, hk_driver, "Cover", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    # Set from HomeKit
    call_stop_cover = async_mock_service(menuai, COVER_DOMAIN, "stop_cover")

    acc.char_hold_position.client_update_value(0)
    await menuai.async_block_till_done()
    assert not call_stop_cover

    acc.char_hold_position.client_update_value(1)
    await menuai.async_block_till_done()
    assert call_stop_cover
    assert call_stop_cover[0].data[ATTR_ENTITY_ID] == entity_id
    assert acc.char_hold_position.value == 1
    assert len(events) == 1
    assert events[-1].data[ATTR_VALUE] is None


async def test_windowcovering_basic_restore(
    menuai: menuai, entity_registry: er.EntityRegistry, hk_driver
) -> None:
    """Test setting up an entity from state in the event registry."""
    menuai.set_state(CoreState.not_running)

    entity_registry.async_get_or_create(
        "cover",
        "generic",
        "1234",
        suggested_object_id="simple",
    )
    entity_registry.async_get_or_create(
        "cover",
        "generic",
        "9012",
        suggested_object_id="all_info_set",
        capabilities={},
        supported_features=CoverEntityFeature.STOP,
        original_device_class="mock-device-class",
    )

    menuai.bus.async_fire(EVENT_menuai_START, {})
    await menuai.async_block_till_done()

    acc = WindowCoveringBasic(menuai, hk_driver, "Cover", "cover.simple", 2, None)
    assert acc.category == 14
    assert acc.char_current_position is not None
    assert acc.char_target_position is not None
    assert acc.char_position_state is not None

    acc = WindowCoveringBasic(menuai, hk_driver, "Cover", "cover.all_info_set", 3, None)
    assert acc.category == 14
    assert acc.char_current_position is not None
    assert acc.char_target_position is not None
    assert acc.char_position_state is not None


async def test_windowcovering_restore(
    menuai: menuai, entity_registry: er.EntityRegistry, hk_driver
) -> None:
    """Test setting up an entity from state in the event entity_registry."""
    menuai.set_state(CoreState.not_running)

    entity_registry.async_get_or_create(
        "cover",
        "generic",
        "1234",
        suggested_object_id="simple",
    )
    entity_registry.async_get_or_create(
        "cover",
        "generic",
        "9012",
        suggested_object_id="all_info_set",
        capabilities={},
        supported_features=CoverEntityFeature.STOP,
        original_device_class="mock-device-class",
    )

    menuai.bus.async_fire(EVENT_menuai_START, {})
    await menuai.async_block_till_done()

    acc = WindowCovering(menuai, hk_driver, "Cover", "cover.simple", 2, None)
    assert acc.category == 14
    assert acc.char_current_position is not None
    assert acc.char_target_position is not None
    assert acc.char_position_state is not None

    acc = WindowCovering(menuai, hk_driver, "Cover", "cover.all_info_set", 3, None)
    assert acc.category == 14
    assert acc.char_current_position is not None
    assert acc.char_target_position is not None
    assert acc.char_position_state is not None


async def test_garage_door_with_linked_obstruction_sensor(
    menuai: menuai, hk_driver
) -> None:
    """Test if accessory and HA are updated accordingly with a linked obstruction sensor."""
    linked_obstruction_sensor_entity_id = "binary_sensor.obstruction"
    entity_id = "cover.garage_door"

    menuai.states.async_set(linked_obstruction_sensor_entity_id, STATE_OFF)
    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = GarageDoorOpener(
        menuai,
        hk_driver,
        "Garage Door",
        entity_id,
        2,
        {CONF_LINKED_OBSTRUCTION_SENSOR: linked_obstruction_sensor_entity_id},
    )
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 4  # GarageDoorOpener

    assert acc.char_current_state.value == HK_DOOR_OPEN
    assert acc.char_target_state.value == HK_DOOR_OPEN

    menuai.states.async_set(entity_id, CoverState.CLOSED)
    await menuai.async_block_till_done()
    assert acc.char_current_state.value == HK_DOOR_CLOSED
    assert acc.char_target_state.value == HK_DOOR_CLOSED
    assert acc.char_obstruction_detected.value is False

    menuai.states.async_set(entity_id, CoverState.OPEN)
    menuai.states.async_set(linked_obstruction_sensor_entity_id, STATE_ON)
    await menuai.async_block_till_done()
    assert acc.char_current_state.value == HK_DOOR_OPEN
    assert acc.char_target_state.value == HK_DOOR_OPEN
    assert acc.char_obstruction_detected.value is True

    menuai.states.async_set(entity_id, CoverState.CLOSED)
    menuai.states.async_set(linked_obstruction_sensor_entity_id, STATE_OFF)
    await menuai.async_block_till_done()
    assert acc.char_current_state.value == HK_DOOR_CLOSED
    assert acc.char_target_state.value == HK_DOOR_CLOSED
    assert acc.char_obstruction_detected.value is False

    menuai.states.async_remove(entity_id)
    menuai.states.async_remove(linked_obstruction_sensor_entity_id)
    await menuai.async_block_till_done()
