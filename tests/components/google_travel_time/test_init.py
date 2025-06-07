"""Tests for Google Maps Travel Time init."""

import pytest

from menuai.components.google_travel_time.const import (
    ARRIVAL_TIME,
    CONF_TIME,
    CONF_TIME_TYPE,
    DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .const import DEFAULT_OPTIONS, MOCK_CONFIG

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("v1", "v2"),
    [
        ("08:00", "08:00"),
        ("08:00:00", "08:00:00"),
        ("1742144400", "17:00"),
        ("now", None),
        (None, None),
    ],
)
@pytest.mark.usefixtures("routes_mock", "mock_setup_entry")
async def test_migrate_entry_v1_v2(
    menuai: menuai,
    v1: str,
    v2: str | None,
) -> None:
    """Test successful migration of entry data."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data=MOCK_CONFIG,
        options={
            **DEFAULT_OPTIONS,
            CONF_TIME_TYPE: ARRIVAL_TIME,
            CONF_TIME: v1,
        },
    )
    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    updated_entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)

    assert updated_entry.state is ConfigEntryState.LOADED
    assert updated_entry.version == 2
    assert updated_entry.options[CONF_TIME] == v2


@pytest.mark.usefixtures("routes_mock", "mock_setup_entry")
async def test_migrate_entry_v1_v2_invalid_time(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test successful migration of entry data."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data=MOCK_CONFIG,
        options={
            **DEFAULT_OPTIONS,
            CONF_TIME_TYPE: ARRIVAL_TIME,
            CONF_TIME: "invalid",
        },
    )
    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    updated_entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)

    assert updated_entry.state is ConfigEntryState.LOADED
    assert updated_entry.version == 2
    assert updated_entry.options[CONF_TIME] is None
    assert "Invalid time format found while migrating" in caplog.text
