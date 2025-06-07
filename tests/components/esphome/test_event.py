"""Test ESPHome Events."""

from aioesphomeapi import APIClient, Event, EventInfo
import pytest

from menuai.components.event import EventDeviceClass
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai


@pytest.mark.freeze_time("2024-04-24 00:00:00+00:00")
async def test_generic_event_entity(
    menuai: menuai,
    mock_client: APIClient,
    mock_esphome_device,
) -> None:
    """Test a generic event entity and its availability behavior."""
    entity_info = [
        EventInfo(
            object_id="myevent",
            key=1,
            name="my event",
            unique_id="my_event",
            event_types=["type1", "type2"],
            device_class=EventDeviceClass.BUTTON,
        )
    ]
    states = [Event(key=1, event_type="type1")]
    user_service = []
    device = await mock_esphome_device(
        mock_client=mock_client,
        entity_info=entity_info,
        user_service=user_service,
        states=states,
    )
    await menuai.async_block_till_done()

    # Test initial state
    state = menuai.states.get("event.test_myevent")
    assert state is not None
    assert state.state == "2024-04-24T00:00:00.000+00:00"
    assert state.attributes["event_type"] == "type1"

    # Test device becomes unavailable
    await device.mock_disconnect(True)
    await menuai.async_block_till_done()
    state = menuai.states.get("event.test_myevent")
    assert state.state == STATE_UNAVAILABLE

    # Test device becomes available again
    await device.mock_connect()
    await menuai.async_block_till_done()

    # Event entity should be available immediately without waiting for data
    state = menuai.states.get("event.test_myevent")
    assert state.state == "2024-04-24T00:00:00.000+00:00"
    assert state.attributes["event_type"] == "type1"
