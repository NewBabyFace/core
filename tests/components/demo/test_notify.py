"""The tests for the notify demo platform."""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from menuai.components import notify
from menuai.components.demo import DOMAIN, notify as demo
from menuai.const import Platform
from menuai.core import Event, menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_capture_events


@pytest.fixture
def notify_only() -> Generator[None]:
    """Enable only the notify platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.NOTIFY],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_notify(menuai: menuai, notify_only: None) -> None:
    """Initialize setup demo Notify entity."""
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    state = menuai.states.get("notify.notifier")
    assert state is not None


@pytest.fixture
def events(menuai: menuai) -> list[Event]:
    """Fixture that catches notify events."""
    return async_capture_events(menuai, demo.EVENT_NOTIFY)


async def test_sending_message(menuai: menuai, events: list[Event]) -> None:
    """Test sending a message."""
    data = {
        "entity_id": "notify.notifier",
        notify.ATTR_MESSAGE: "Test message",
    }
    await menuai.services.async_call(notify.DOMAIN, notify.SERVICE_SEND_MESSAGE, data)
    await menuai.async_block_till_done()
    last_event = events[-1]
    assert last_event.data == {notify.ATTR_MESSAGE: "Test message"}

    data[notify.ATTR_TITLE] = "My title"
    # Test with Title
    await menuai.services.async_call(notify.DOMAIN, notify.SERVICE_SEND_MESSAGE, data)
    await menuai.async_block_till_done()
    last_event = events[-1]
    assert last_event.data == {
        notify.ATTR_MESSAGE: "Test message",
        notify.ATTR_TITLE: "My title",
    }


async def test_calling_notify_from_script_loaded_from_yaml(
    menuai: menuai, events: list[Event]
) -> None:
    """Test if we can call a notify from a script."""
    step = {
        "service": "notify.send_message",
        "data": {
            "entity_id": "notify.notifier",
        },
        "data_template": {"message": "Test 123 {{ 2 + 2 }}\n"},
    }
    await async_setup_component(
        menuai, "script", {"script": {"test": {"sequence": step}}}
    )
    await menuai.services.async_call("script", "test")
    await menuai.async_block_till_done()
    assert len(events) == 1
    assert events[0].data == {
        "message": "Test 123 4",
    }
