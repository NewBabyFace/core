"""Test the update significant change platform."""

from menuai.components.update.const import (
    ATTR_IN_PROGRESS,
    ATTR_INSTALLED_VERSION,
    ATTR_LATEST_VERSION,
    ATTR_RELEASE_SUMMARY,
    ATTR_RELEASE_URL,
    ATTR_SKIPPED_VERSION,
    ATTR_TITLE,
)
from menuai.components.update.significant_change import (
    async_check_significant_change,
)
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai


async def test_significant_change(menuai: menuai) -> None:
    """Detect update significant changes."""
    assert async_check_significant_change(menuai, STATE_ON, {}, STATE_OFF, {})
    assert async_check_significant_change(menuai, STATE_OFF, {}, STATE_ON, {})
    assert not async_check_significant_change(menuai, STATE_OFF, {}, STATE_OFF, {})
    assert not async_check_significant_change(menuai, STATE_ON, {}, STATE_ON, {})

    attrs = {
        ATTR_INSTALLED_VERSION: "1.0.0",
        ATTR_IN_PROGRESS: False,
        ATTR_LATEST_VERSION: "1.0.1",
        ATTR_RELEASE_SUMMARY: "Fixes!",
        ATTR_RELEASE_URL: "https://www.example.com",
        ATTR_SKIPPED_VERSION: None,
        ATTR_TITLE: "Piece of Software",
    }
    assert not async_check_significant_change(menuai, STATE_ON, attrs, STATE_ON, attrs)

    assert async_check_significant_change(
        menuai,
        STATE_ON,
        attrs,
        STATE_ON,
        attrs.copy() | {ATTR_INSTALLED_VERSION: "1.0.1"},
    )

    assert async_check_significant_change(
        menuai,
        STATE_ON,
        attrs,
        STATE_ON,
        attrs.copy() | {ATTR_LATEST_VERSION: "1.0.2"},
    )

    assert not async_check_significant_change(
        menuai,
        STATE_ON,
        attrs,
        STATE_ON,
        attrs.copy() | {ATTR_IN_PROGRESS: True},
    )

    assert not async_check_significant_change(
        menuai,
        STATE_ON,
        attrs,
        STATE_ON,
        attrs.copy() | {ATTR_RELEASE_SUMMARY: "More fixes!"},
    )

    assert not async_check_significant_change(
        menuai,
        STATE_ON,
        attrs,
        STATE_ON,
        attrs.copy() | {ATTR_RELEASE_URL: "https://www.example.com/changed_url"},
    )

    assert not async_check_significant_change(
        menuai,
        STATE_ON,
        attrs,
        STATE_ON,
        attrs.copy() | {ATTR_SKIPPED_VERSION: "1.0.0"},
    )

    assert not async_check_significant_change(
        menuai,
        STATE_ON,
        attrs,
        STATE_ON,
        attrs.copy() | {ATTR_TITLE: "Renamed the software..."},
    )
