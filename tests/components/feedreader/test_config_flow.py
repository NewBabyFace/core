"""The tests for the feedreader config flow."""

from unittest.mock import Mock, patch
import urllib

import pytest

from menuai.components.feedreader.const import (
    CONF_MAX_ENTRIES,
    DEFAULT_MAX_ENTRIES,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_URL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import create_mock_entry
from .const import FEED_TITLE, URL, VALID_CONFIG_DEFAULT


@pytest.fixture(name="feedparser")
def feedparser_fixture(feed_one_event: bytes) -> Mock:
    """Patch libraries."""
    with (
        patch(
            "menuai.components.feedreader.config_flow.feedparser.http.get",
            return_value=feed_one_event,
        ) as feedparser,
    ):
        yield feedparser


@pytest.fixture(name="setup_entry")
def setup_entry_fixture(feed_one_event: bytes) -> Mock:
    """Patch libraries."""
    with (
        patch("menuai.components.feedreader.async_setup_entry") as setup_entry,
    ):
        yield setup_entry


async def test_user(menuai: menuai, feedparser, setup_entry) -> None:
    """Test starting a flow by user."""
    # init user flow
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # success
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_URL: URL}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == FEED_TITLE
    assert result["data"][CONF_URL] == URL
    assert result["options"][CONF_MAX_ENTRIES] == DEFAULT_MAX_ENTRIES


async def test_user_errors(
    menuai: menuai, feedparser, setup_entry, feed_one_event
) -> None:
    """Test starting a flow by user which results in an URL error."""
    # init user flow
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # raise URLError
    feedparser.side_effect = urllib.error.URLError("Test")
    feedparser.return_value = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_URL: URL}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "url_error"}

    # success
    feedparser.side_effect = None
    feedparser.return_value = feed_one_event
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_URL: URL}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == FEED_TITLE
    assert result["data"][CONF_URL] == URL
    assert result["options"][CONF_MAX_ENTRIES] == DEFAULT_MAX_ENTRIES


async def test_reconfigure(menuai: menuai, feedparser) -> None:
    """Test starting a reconfigure flow."""
    entry = create_mock_entry(VALID_CONFIG_DEFAULT)
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    # init user flow
    result = await entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # success
    with patch(
        "menuai.config_entries.ConfigEntries.async_reload"
    ) as mock_async_reload:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_URL: "http://other.rss.local/rss_feed.xml",
            },
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_URL: "http://other.rss.local/rss_feed.xml",
    }

    await menuai.async_block_till_done()
    assert mock_async_reload.call_count == 1


async def test_reconfigure_errors(
    menuai: menuai, feedparser, setup_entry, feed_one_event
) -> None:
    """Test starting a reconfigure flow by user which results in an URL error."""
    entry = create_mock_entry(VALID_CONFIG_DEFAULT)
    entry.add_to_menuai(menuai)

    # init user flow
    result = await entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # raise URLError
    feedparser.side_effect = urllib.error.URLError("Test")
    feedparser.return_value = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_URL: "http://other.rss.local/rss_feed.xml",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "url_error"}

    # success
    feedparser.side_effect = None
    feedparser.return_value = feed_one_event

    # success
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_URL: "http://other.rss.local/rss_feed.xml",
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_URL: "http://other.rss.local/rss_feed.xml",
    }


async def test_options_flow(menuai: menuai) -> None:
    """Test options flow."""
    entry = create_mock_entry(VALID_CONFIG_DEFAULT)
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MAX_ENTRIES: 10,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_MAX_ENTRIES: 10,
    }


@pytest.mark.parametrize(
    ("fixture_name", "expected_title"),
    [
        ("feed_htmlentities", "RSS en español"),
        ("feed_atom_htmlentities", "ATOM RSS en español"),
    ],
)
async def test_feed_htmlentities(
    menuai: menuai,
    feedparser,
    setup_entry,
    fixture_name,
    expected_title,
    request: pytest.FixtureRequest,
) -> None:
    """Test starting a flow by user from a feed with HTML Entities in the title."""
    with patch(
        "menuai.components.feedreader.config_flow.feedparser.http.get",
        side_effect=[request.getfixturevalue(fixture_name)],
    ):
        # init user flow
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        # success
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_URL: URL}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == expected_title
