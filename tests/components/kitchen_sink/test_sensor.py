"""The tests for the kitchen_sink sensor platform."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai import config_entries
from menuai.components.kitchen_sink import DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


@pytest.fixture
async def sensor_only() -> None:
    """Enable only the sensor platform."""
    with patch(
        "menuai.components.kitchen_sink.COMPONENTS_WITH_DEMO_PLATFORM",
        [Platform.SENSOR],
    ):
        yield


@pytest.fixture
async def setup_comp(menuai: menuai, sensor_only):
    """Set up demo component."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("setup_comp")
async def test_states(menuai: menuai, snapshot: SnapshotAssertion) -> None:
    """Test the expected sensor entities are added."""
    states = menuai.states.async_all()
    assert set(states) == snapshot


@pytest.mark.usefixtures("sensor_only")
async def test_states_with_subentry(
    menuai: menuai, snapshot: SnapshotAssertion
) -> None:
    """Test the expected sensor entities are added."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        subentries_data=[
            config_entries.ConfigSubentryData(
                data={"state": 15},
                subentry_id="blabla",
                subentry_type="entity",
                title="Sensor test",
                unique_id=None,
            )
        ],
    )
    config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    states = menuai.states.async_all()
    assert set(states) == snapshot
