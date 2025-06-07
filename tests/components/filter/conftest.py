"""Fixtures for the Filter integration."""

from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.filter.const import (
    CONF_FILTER_NAME,
    CONF_FILTER_PRECISION,
    CONF_FILTER_RADIUS,
    CONF_FILTER_WINDOW_SIZE,
    DEFAULT_FILTER_RADIUS,
    DEFAULT_NAME,
    DEFAULT_PRECISION,
    DEFAULT_WINDOW_SIZE,
    DOMAIN,
    FILTER_NAME_OUTLIER,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_ENTITY_ID, CONF_NAME
from menuai.core import menuai, State
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry


@pytest.fixture(name="values")
def values_fixture() -> list[State]:
    """Fixture for a list of test States."""
    values = []
    raw_values = [20, 19, 18, 21, 22, 0]
    timestamp = dt_util.utcnow()
    for val in raw_values:
        values.append(State("sensor.test_monitored", str(val), last_updated=timestamp))
        timestamp += timedelta(minutes=1)
    return values


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Automatically patch setup_entry."""
    with patch(
        "menuai.components.filter.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(name="get_config")
async def get_config_to_integration_load() -> dict[str, Any]:
    """Return configuration.

    To override the config, tests can be marked with:
    @pytest.mark.parametrize("get_config", [{...}])
    """
    return {
        CONF_NAME: DEFAULT_NAME,
        CONF_ENTITY_ID: "sensor.test_monitored",
        CONF_FILTER_NAME: FILTER_NAME_OUTLIER,
        CONF_FILTER_WINDOW_SIZE: DEFAULT_WINDOW_SIZE,
        CONF_FILTER_RADIUS: DEFAULT_FILTER_RADIUS,
        CONF_FILTER_PRECISION: DEFAULT_PRECISION,
    }


@pytest.fixture(name="loaded_entry")
async def load_integration(
    menuai: menuai, get_config: dict[str, Any], values: list[State]
) -> MockConfigEntry:
    """Set up the Filter integration in MenuAI."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        options=get_config,
        entry_id="1",
    )

    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    for value in values:
        menuai.states.async_set(get_config["entity_id"], value.state)
        await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    return config_entry
