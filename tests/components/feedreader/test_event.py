"""The tests for the feedreader event entity."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.feedreader.event import (
    ATTR_CONTENT,
    ATTR_DESCRIPTION,
    ATTR_LINK,
    ATTR_TITLE,
)
from menuai.core import menuai
from menuai.util import dt as dt_util

from . import create_mock_entry
from .const import VALID_CONFIG_DEFAULT

from tests.common import async_fire_time_changed


async def test_event_entity(
    menuai: menuai, feed_one_event, feed_two_event, feed_only_summary
) -> None:
    """Test feed event entity."""
    entry = create_mock_entry(VALID_CONFIG_DEFAULT)
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.feedreader.coordinator.feedparser.http.get",
        side_effect=[feed_one_event, feed_two_event, feed_only_summary],
    ):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        state = menuai.states.get("event.mock_title")
        assert state
        assert state.attributes[ATTR_TITLE] == "Title 1"
        assert state.attributes[ATTR_LINK] == "http://www.example.com/link/1"
        assert state.attributes[ATTR_CONTENT] == "Content 1"
        assert state.attributes[ATTR_DESCRIPTION] == "Description 1"

        future = dt_util.utcnow() + timedelta(hours=1, seconds=1)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done(wait_background_tasks=True)

        state = menuai.states.get("event.mock_title")
        assert state
        assert state.attributes[ATTR_TITLE] == "Title 2"
        assert state.attributes[ATTR_LINK] == "http://www.example.com/link/2"
        assert state.attributes[ATTR_CONTENT] == "Content 2"
        assert state.attributes[ATTR_DESCRIPTION] == "Description 2"

        future = dt_util.utcnow() + timedelta(hours=2, seconds=2)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done(wait_background_tasks=True)

        state = menuai.states.get("event.mock_title")
        assert state
        assert state.attributes[ATTR_TITLE] == "Title 1"
        assert state.attributes[ATTR_LINK] == "http://www.example.com/link/1"
        assert state.attributes[ATTR_CONTENT] == "This is a summary"
        assert state.attributes[ATTR_DESCRIPTION] == "Description 1"


@pytest.mark.parametrize(
    ("fixture_name"),
    [
        ("feed_htmlentities"),
        ("feed_atom_htmlentities"),
    ],
)
async def test_event_htmlentities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    fixture_name,
    request: pytest.FixtureRequest,
) -> None:
    """Test feed event entity with HTML Entities."""
    entry = create_mock_entry(VALID_CONFIG_DEFAULT)
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.feedreader.coordinator.feedparser.http.get",
        side_effect=[request.getfixturevalue(fixture_name)],
    ):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        state = menuai.states.get("event.mock_title")
        assert state
        assert state.attributes == snapshot
