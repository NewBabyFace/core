"""The tests for mobile_app logbook."""

from menuai.components.mobile_app.logbook import (
    DOMAIN,
    IOS_EVENT_ZONE_ENTERED,
    IOS_EVENT_ZONE_EXITED,
)
from menuai.const import ATTR_FRIENDLY_NAME, ATTR_ICON
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.components.logbook.common import MockRow, mock_humanify


async def test_humanify_ios_events(menuai: menuai) -> None:
    """Test humanifying ios events."""
    menuai.config.components.add("recorder")
    assert await async_setup_component(menuai, "logbook", {})
    await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    menuai.states.async_set(
        "zone.bad_place",
        "0",
        {ATTR_FRIENDLY_NAME: "passport control", ATTR_ICON: "mdi:airplane-marker"},
    )
    await menuai.async_block_till_done()

    (event1, event2) = mock_humanify(
        menuai,
        [
            MockRow(
                IOS_EVENT_ZONE_ENTERED,
                {"sourceDeviceName": "test_phone", "zone": "zone.happy_place"},
            ),
            MockRow(
                IOS_EVENT_ZONE_EXITED,
                {"sourceDeviceName": "test_phone", "zone": "zone.bad_place"},
            ),
        ],
    )

    assert event1["name"] == "test_phone"
    assert event1["domain"] == DOMAIN
    assert event1["message"] == "entered zone zone.happy_place"
    assert event1["icon"] == "mdi:crosshairs-gps"
    assert event1["entity_id"] == "zone.happy_place"

    assert event2["name"] == "test_phone"
    assert event2["domain"] == DOMAIN
    assert event2["message"] == "exited zone passport control"
    assert event2["icon"] == "mdi:airplane-marker"
    assert event2["entity_id"] == "zone.bad_place"
