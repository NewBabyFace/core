"""The tests for Google Assistant logbook."""

from menuai.components.google_assistant.const import (
    DOMAIN,
    EVENT_COMMAND_RECEIVED,
    SOURCE_CLOUD,
    SOURCE_LOCAL,
)
from menuai.const import ATTR_ENTITY_ID, ATTR_FRIENDLY_NAME
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.components.logbook.common import MockRow, mock_humanify


async def test_humanify_command_received(menuai: menuai) -> None:
    """Test humanifying command event."""
    menuai.config.components.add("recorder")
    menuai.config.components.add("frontend")
    menuai.config.components.add("google_assistant")
    assert await async_setup_component(menuai, "logbook", {})
    await menuai.async_block_till_done()

    menuai.states.async_set(
        "light.kitchen", "on", {ATTR_FRIENDLY_NAME: "The Kitchen Lights"}
    )

    events = mock_humanify(
        menuai,
        [
            MockRow(
                EVENT_COMMAND_RECEIVED,
                {
                    "request_id": "abcd",
                    ATTR_ENTITY_ID: ["light.kitchen"],
                    "execution": [
                        {
                            "command": "action.devices.commands.OnOff",
                            "params": {"on": True},
                        }
                    ],
                    "source": SOURCE_LOCAL,
                },
            ),
            MockRow(
                EVENT_COMMAND_RECEIVED,
                {
                    "request_id": "abcd",
                    ATTR_ENTITY_ID: ["light.non_existing"],
                    "execution": [
                        {
                            "command": "action.devices.commands.OnOff",
                            "params": {"on": False},
                        }
                    ],
                    "source": SOURCE_CLOUD,
                },
            ),
        ],
    )

    assert len(events) == 2
    event1, event2 = events

    assert event1["name"] == "Google Assistant"
    assert event1["domain"] == DOMAIN
    assert event1["message"] == "sent command OnOff (via local)"

    assert event2["name"] == "Google Assistant"
    assert event2["domain"] == DOMAIN
    assert event2["message"] == "sent command OnOff"
