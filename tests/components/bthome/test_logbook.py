"""The tests for bthome logbook."""

from menuai.components.bthome.const import (
    BTHOME_BLE_EVENT,
    DOMAIN,
    BTHomeBleEvent,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.components.logbook.common import MockRow, mock_humanify


async def test_humanify_bthome_event(menuai: menuai) -> None:
    """Test humanifying bthome button presses."""
    menuai.config.components.add("recorder")
    assert await async_setup_component(menuai, "logbook", {})
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="A4:C1:38:8D:18:B2",
    )
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    (event1, event2) = mock_humanify(
        menuai,
        [
            MockRow(
                BTHOME_BLE_EVENT,
                dict(
                    BTHomeBleEvent(
                        device_id=None,
                        address="A4:C1:38:8D:18:B2",
                        event_class="button",
                        event_type="long_press",
                        event_properties={
                            "any": "thing",
                        },
                    )
                ),
            ),
            MockRow(
                BTHOME_BLE_EVENT,
                dict(
                    BTHomeBleEvent(
                        device_id=None,
                        address="A4:C1:38:8D:18:B2",
                        event_class="button",
                        event_type="press",
                        event_properties=None,
                    )
                ),
            ),
        ],
    )

    assert event1["name"] == "BTHome A4:C1:38:8D:18:B2"
    assert event1["domain"] == DOMAIN
    assert event1["message"] == "button long_press: {'any': 'thing'}"

    assert event2["name"] == "BTHome A4:C1:38:8D:18:B2"
    assert event2["domain"] == DOMAIN
    assert event2["message"] == "button press"
