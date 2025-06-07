"""Tests for the tag component."""

from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.tag import DOMAIN, EVENT_TAG_SCANNED, async_scan_tag
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import TEST_DEVICE_ID, TEST_TAG_ID, TEST_TAG_NAME

from tests.common import async_capture_events
from tests.typing import WebSocketGenerator


@pytest.fixture
def storage_setup_named_tag(
    menuai: menuai,
    menuai_storage: dict[str, Any],
):
    """Storage setup for test case of named tags."""

    async def _storage(items=None):
        if items is None:
            menuai_storage[DOMAIN] = {
                "key": DOMAIN,
                "version": 1,
                "minor_version": 2,
                "data": {
                    "items": [
                        {
                            "id": TEST_TAG_ID,
                            "tag_id": TEST_TAG_ID,
                        }
                    ]
                },
            }
        else:
            menuai_storage[DOMAIN] = items
        entity_registry = er.async_get(menuai)
        entry = entity_registry.async_get_or_create(DOMAIN, DOMAIN, TEST_TAG_ID)
        entity_registry.async_update_entity(entry.entity_id, name=TEST_TAG_NAME)
        config = {DOMAIN: {}}
        return await async_setup_component(menuai, DOMAIN, config)

    return _storage


async def test_named_tag_scanned_event(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
    storage_setup_named_tag,
) -> None:
    """Test scanning named tag triggering event."""
    assert await storage_setup_named_tag()

    await menuai_ws_client(menuai)

    events = async_capture_events(menuai, EVENT_TAG_SCANNED)

    now = dt_util.utcnow()
    freezer.move_to(now)
    await async_scan_tag(menuai, TEST_TAG_ID, TEST_DEVICE_ID)

    assert len(events) == 1

    event = events[0]
    event_data = event.data

    assert event_data["name"] == TEST_TAG_NAME
    assert event_data["device_id"] == TEST_DEVICE_ID
    assert event_data["tag_id"] == TEST_TAG_ID


@pytest.fixture
def storage_setup_unnamed_tag(menuai: menuai, menuai_storage: dict[str, Any]):
    """Storage setup for test case of unnamed tags."""

    async def _storage(items=None):
        if items is None:
            menuai_storage[DOMAIN] = {
                "key": DOMAIN,
                "version": 1,
                "minor_version": 2,
                "data": {"items": [{"id": TEST_TAG_ID, "tag_id": TEST_TAG_ID}]},
            }
        else:
            menuai_storage[DOMAIN] = items
        config = {DOMAIN: {}}
        return await async_setup_component(menuai, DOMAIN, config)

    return _storage


async def test_unnamed_tag_scanned_event(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
    storage_setup_unnamed_tag,
) -> None:
    """Test scanning named tag triggering event."""
    assert await storage_setup_unnamed_tag()

    await menuai_ws_client(menuai)

    events = async_capture_events(menuai, EVENT_TAG_SCANNED)

    now = dt_util.utcnow()
    freezer.move_to(now)
    await async_scan_tag(menuai, TEST_TAG_ID, TEST_DEVICE_ID)

    assert len(events) == 1

    event = events[0]
    event_data = event.data

    assert event_data["name"] == "Tag test tag id"
    assert event_data["device_id"] == TEST_DEVICE_ID
    assert event_data["tag_id"] == TEST_TAG_ID
