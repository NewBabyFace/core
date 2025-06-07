"""Test DoorBird events."""

from menuai.const import STATE_UNKNOWN
from menuai.core import menuai

from . import mock_webhook_call
from .conftest import DoorbirdMockerType

from tests.typing import ClientSessionGenerator


async def test_doorbell_ring_event(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    doorbird_mocker: DoorbirdMockerType,
) -> None:
    """Test a doorbell ring event."""
    doorbird_entry = await doorbird_mocker()
    relay_1_entity_id = "event.mydoorbird_doorbell"
    assert menuai.states.get(relay_1_entity_id).state == STATE_UNKNOWN
    client = await menuai_client()
    await mock_webhook_call(doorbird_entry.entry, client, "mydoorbird_doorbell")
    assert menuai.states.get(relay_1_entity_id).state != STATE_UNKNOWN


async def test_motion_event(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    doorbird_mocker: DoorbirdMockerType,
) -> None:
    """Test a doorbell motion event."""
    doorbird_entry = await doorbird_mocker()
    relay_1_entity_id = "event.mydoorbird_motion"
    assert menuai.states.get(relay_1_entity_id).state == STATE_UNKNOWN
    client = await menuai_client()
    await mock_webhook_call(doorbird_entry.entry, client, "mydoorbird_motion")
    assert menuai.states.get(relay_1_entity_id).state != STATE_UNKNOWN
