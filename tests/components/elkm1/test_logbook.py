"""The tests for elkm1 logbook."""

from menuai.components.elkm1.const import (
    ATTR_KEY,
    ATTR_KEY_NAME,
    ATTR_KEYPAD_ID,
    ATTR_KEYPAD_NAME,
    DOMAIN,
    EVENT_ELKM1_KEYPAD_KEY_PRESSED,
)
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import _patch_discovery, _patch_elk

from tests.common import MockConfigEntry
from tests.components.logbook.common import MockRow, mock_humanify


async def test_humanify_elkm1_keypad_event(menuai: menuai) -> None:
    """Test humanifying elkm1 keypad presses."""
    menuai.config.components.add("recorder")
    assert await async_setup_component(menuai, "logbook", {})
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "elks://1.2.3.4"},
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    config_entry.add_to_menuai(menuai)

    with _patch_discovery(), _patch_elk():
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    (event1, event2) = mock_humanify(
        menuai,
        [
            MockRow(
                EVENT_ELKM1_KEYPAD_KEY_PRESSED,
                {
                    ATTR_KEYPAD_ID: 1,
                    ATTR_KEY_NAME: "four",
                    ATTR_KEY: "4",
                    ATTR_KEYPAD_NAME: "Main Bedroom",
                },
            ),
            MockRow(
                EVENT_ELKM1_KEYPAD_KEY_PRESSED,
                {
                    ATTR_KEYPAD_ID: 1,
                    ATTR_KEY_NAME: "five",
                    ATTR_KEY: "5",
                },
            ),
        ],
    )

    assert event1["name"] == "Elk Keypad Main Bedroom"
    assert event1["domain"] == DOMAIN
    assert event1["message"] == "pressed four (4)"

    assert event2["name"] == "Elk Keypad 1"
    assert event2["domain"] == DOMAIN
    assert event2["message"] == "pressed five (5)"
