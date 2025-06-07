"""The tests for the PG LAB Electronics cover."""

from menuai.components import cover
from menuai.components.cover import (
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
)
from menuai.const import (
    ATTR_ASSUMED_STATE,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    STATE_UNKNOWN,
)
from menuai.core import menuai

from .test_common import get_device_discovery_payload, send_discovery_message

from tests.common import async_fire_mqtt_message
from tests.typing import MqttMockHAClient

COVER_FEATURES = (
    cover.CoverEntityFeature.OPEN
    | cover.CoverEntityFeature.CLOSE
    | cover.CoverEntityFeature.STOP
)


async def call_service(menuai: menuai, entity_id, service, **kwargs):
    """Call a service."""
    await menuai.services.async_call(
        COVER_DOMAIN,
        service,
        {"entity_id": entity_id, **kwargs},
        blocking=True,
    )


async def test_cover_features(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_pglab
) -> None:
    """Test cover features."""

    payload = get_device_discovery_payload(
        number_of_shutters=4,
        number_of_boards=1,
    )

    await send_discovery_message(menuai, payload)

    assert len(menuai.states.async_all("cover")) == 4

    for i in range(4):
        cover = menuai.states.get(f"cover.test_shutter_{i}")
        assert cover
        assert cover.attributes["supported_features"] == COVER_FEATURES


async def test_cover_availability(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_pglab
) -> None:
    """Check if covers are properly created."""

    payload = get_device_discovery_payload(
        number_of_shutters=6,
        number_of_boards=2,
    )

    await send_discovery_message(menuai, payload)

    # We are creating 6 covers using two E-RELAY devices connected to E-BOARD.
    # Now we are going to check if all covers are created and their state is unknown.
    for i in range(5):
        cover = menuai.states.get(f"cover.test_shutter_{i}")
        assert cover.state == STATE_UNKNOWN
        assert not cover.attributes.get(ATTR_ASSUMED_STATE)

    # The cover with id 7 should not be created.
    cover = menuai.states.get("cover.test_shutter_7")
    assert not cover


async def test_cover_change_state_via_mqtt(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_pglab
) -> None:
    """Test state update via MQTT."""
    payload = get_device_discovery_payload(
        number_of_shutters=2,
        number_of_boards=1,
    )

    await send_discovery_message(menuai, payload)

    # Check initial state is unknown
    cover = menuai.states.get("cover.test_shutter_0")
    assert cover.state == STATE_UNKNOWN
    assert not cover.attributes.get(ATTR_ASSUMED_STATE)

    # Simulate the device responds sending mqtt messages and check if the cover state
    # change appropriately.

    async_fire_mqtt_message(menuai, "pglab/test/shutter/0/state", "OPEN")
    await menuai.async_block_till_done()
    cover = menuai.states.get("cover.test_shutter_0")
    assert not cover.attributes.get(ATTR_ASSUMED_STATE)
    assert cover.state == STATE_OPEN

    async_fire_mqtt_message(menuai, "pglab/test/shutter/0/state", "OPENING")
    await menuai.async_block_till_done()
    cover = menuai.states.get("cover.test_shutter_0")
    assert cover.state == STATE_OPENING

    async_fire_mqtt_message(menuai, "pglab/test/shutter/0/state", "CLOSING")
    await menuai.async_block_till_done()
    cover = menuai.states.get("cover.test_shutter_0")
    assert cover.state == STATE_CLOSING

    async_fire_mqtt_message(menuai, "pglab/test/shutter/0/state", "CLOSED")
    await menuai.async_block_till_done()
    cover = menuai.states.get("cover.test_shutter_0")
    assert cover.state == STATE_CLOSED


async def test_cover_mqtt_state_by_calling_service(
    menuai: menuai, mqtt_mock: MqttMockHAClient, setup_pglab
) -> None:
    """Calling service to OPEN/CLOSE cover and check mqtt state."""

    payload = get_device_discovery_payload(
        number_of_shutters=2,
        number_of_boards=1,
    )

    await send_discovery_message(menuai, payload)

    cover = menuai.states.get("cover.test_shutter_0")
    assert cover.state == STATE_UNKNOWN
    assert not cover.attributes.get(ATTR_ASSUMED_STATE)

    # Call HA covers services and verify that the MQTT messages are sent correctly

    await call_service(menuai, "cover.test_shutter_0", SERVICE_OPEN_COVER)
    mqtt_mock.async_publish.assert_called_once_with(
        "pglab/test/shutter/0/set", "OPEN", 0, False
    )
    mqtt_mock.async_publish.reset_mock()

    await call_service(menuai, "cover.test_shutter_0", SERVICE_STOP_COVER)
    mqtt_mock.async_publish.assert_called_once_with(
        "pglab/test/shutter/0/set", "STOP", 0, False
    )
    mqtt_mock.async_publish.reset_mock()

    await call_service(menuai, "cover.test_shutter_0", SERVICE_CLOSE_COVER)
    mqtt_mock.async_publish.assert_called_once_with(
        "pglab/test/shutter/0/set", "CLOSE", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
