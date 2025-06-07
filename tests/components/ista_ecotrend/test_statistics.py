"""Tests for the ista EcoTrend Statistics import."""

import datetime
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.recorder.statistics import statistics_during_period
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import extend_statistics

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done


@pytest.mark.usefixtures("recorder_mock", "entity_registry_enabled_by_default")
async def test_statistics_import(
    menuai: menuai,
    ista_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    mock_ista: MagicMock,
    snapshot: SnapshotAssertion,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test setup of ista EcoTrend sensor platform."""

    ista_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(ista_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert ista_config_entry.state is ConfigEntryState.LOADED
    entities = er.async_entries_for_config_entry(
        entity_registry, ista_config_entry.entry_id
    )
    await async_wait_recording_done(menuai)

    # Test that consumption statistics for 2 months have been added
    for entity in entities:
        statistic_id = f"ista_ecotrend:{entity.entity_id.removeprefix('sensor.')}"
        stats = await menuai.async_add_executor_job(
            statistics_during_period,
            menuai,
            datetime.datetime.fromtimestamp(0, tz=datetime.UTC),
            None,
            {statistic_id},
            "month",
            None,
            {"state", "sum"},
        )
        assert stats[statistic_id] == snapshot(name=f"{statistic_id}_2months")
        assert len(stats[statistic_id]) == 2

    # Add another monthly consumption and forward
    # 1 day and test if the new values have been
    # appended to the statistics
    mock_ista.get_consumption_data = extend_statistics

    freezer.tick(datetime.timedelta(days=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    await async_wait_recording_done(menuai)
    freezer.tick(datetime.timedelta(days=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    await async_wait_recording_done(menuai)

    for entity in entities:
        statistic_id = f"ista_ecotrend:{entity.entity_id.removeprefix('sensor.')}"
        stats = await menuai.async_add_executor_job(
            statistics_during_period,
            menuai,
            datetime.datetime.fromtimestamp(0, tz=datetime.UTC),
            None,
            {statistic_id},
            "month",
            None,
            {"state", "sum"},
        )
        assert stats[statistic_id] == snapshot(name=f"{statistic_id}_3months")

        assert len(stats[statistic_id]) == 3


@pytest.mark.usefixtures("recorder_mock", "mock_ista")
async def test_remove(
    menuai: menuai,
    ista_config_entry: MockConfigEntry,
) -> None:
    """Test remove config entry and clear statistics."""
    ista_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(ista_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert ista_config_entry.state is ConfigEntryState.LOADED
    await async_wait_recording_done(menuai)

    assert await menuai.async_add_executor_job(
        statistics_during_period,
        menuai,
        datetime.datetime.fromtimestamp(0, tz=datetime.UTC),
        None,
        {"ista_ecotrend:bahnhofsstr_1a_heating"},
        "month",
        None,
        {"state", "sum"},
    )

    assert await menuai.config_entries.async_unload(ista_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert ista_config_entry.state is ConfigEntryState.NOT_LOADED
    await async_wait_recording_done(menuai)

    assert await menuai.async_add_executor_job(
        statistics_during_period,
        menuai,
        datetime.datetime.fromtimestamp(0, tz=datetime.UTC),
        None,
        {"ista_ecotrend:bahnhofsstr_1a_heating"},
        "month",
        None,
        {"state", "sum"},
    )

    assert await menuai.config_entries.async_remove(ista_config_entry.entry_id)
    await menuai.async_block_till_done()

    await async_wait_recording_done(menuai)

    assert not await menuai.async_add_executor_job(
        statistics_during_period,
        menuai,
        datetime.datetime.fromtimestamp(0, tz=datetime.UTC),
        None,
        {"ista_ecotrend:bahnhofsstr_1a_heating"},
        "month",
        None,
        {"state", "sum"},
    )
