"""The tests for the Rfxtrx sensor platform."""

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from RFXtrx import ControlEvent
from syrupy.assertion import SnapshotAssertion

from menuai.components.rfxtrx import get_rfx_object
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import setup_rfx_test_cfg


@pytest.fixture(autouse=True)
def required_platforms_only():
    """Only set up the required platform and required base platforms to speed up tests."""
    with patch(
        "menuai.components.rfxtrx.PLATFORMS",
        (Platform.EVENT,),
    ):
        yield


async def test_control_event(
    menuai: menuai,
    rfxtrx,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test event update updates correct event object."""
    await menuai.config.async_set_time_zone("UTC")
    freezer.move_to("2021-01-09 12:00:00+00:00")

    await setup_rfx_test_cfg(
        menuai,
        devices={
            "0710013d43010150": {},
            "0710013d44010150": {},
        },
    )

    assert menuai.states.get("event.arc_c1") == snapshot(name="1")
    assert menuai.states.get("event.arc_d1") == snapshot(name="2")

    # only signal one, to make sure we have no overhearing
    await rfxtrx.signal("0710013d44010150")

    assert menuai.states.get("event.arc_c1") == snapshot(diff="1")
    assert menuai.states.get("event.arc_d1") == snapshot(diff="2")


async def test_status_event(
    menuai: menuai,
    rfxtrx,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test event update updates correct event object."""
    await menuai.config.async_set_time_zone("UTC")
    freezer.move_to("2021-01-09 12:00:00+00:00")

    await setup_rfx_test_cfg(
        menuai,
        devices={
            "0820004dd3dc540089": {},
        },
    )

    assert menuai.states.get("event.x10_security_d3dc54_32") == snapshot(name="1")

    await rfxtrx.signal("0820004dd3dc540089")

    assert menuai.states.get("event.x10_security_d3dc54_32") == snapshot(diff="1")


async def test_invalid_event_type(
    menuai: menuai,
    rfxtrx,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test with 1 sensor."""
    await setup_rfx_test_cfg(
        menuai,
        devices={
            "0710013d43010150": {},
        },
    )

    state = menuai.states.get("event.arc_c1")

    # Invalid event type should not trigger change
    event = get_rfx_object("0710013d43010150")
    assert isinstance(event, ControlEvent)
    event.values["Command"] = "invalid_command"

    rfxtrx.event_callback(event)
    await menuai.async_block_till_done()

    assert menuai.states.get("event.arc_c1") == state


async def test_ignoring_lighting4(
    menuai: menuai, entity_registry: er.EntityRegistry, rfxtrx
) -> None:
    """Test with 1 sensor."""
    entry = await setup_rfx_test_cfg(
        menuai,
        devices={
            "0913000022670e013970": {
                "data_bits": 4,
                "command_on": 0xE,
                "command_off": 0x7,
            }
        },
    )

    entries = [
        entry
        for entry in entity_registry.entities.get_entries_for_config_entry_id(
            entry.entry_id
        )
        if entry.domain == Platform.EVENT
    ]
    assert entries == []
