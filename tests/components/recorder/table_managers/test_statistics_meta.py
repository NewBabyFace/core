"""The tests for the Recorder component."""

from __future__ import annotations

import logging
import threading

import pytest

from menuai.components import recorder
from menuai.components.recorder.db_schema import StatisticsMeta
from menuai.components.recorder.models import (
    StatisticMeanType,
    StatisticMetaData,
)
from menuai.components.recorder.util import session_scope
from menuai.const import DEGREE
from menuai.core import menuai

from tests.typing import RecorderInstanceGenerator


async def test_passing_mutually_exclusive_options_to_get_many(
    async_setup_recorder_instance: RecorderInstanceGenerator, menuai: menuai
) -> None:
    """Test passing mutually exclusive options to get_many."""
    instance = await async_setup_recorder_instance(
        menuai, {recorder.CONF_COMMIT_INTERVAL: 0}
    )
    with session_scope(session=instance.get_session()) as session:
        with pytest.raises(ValueError):
            instance.statistics_meta_manager.get_many(
                session,
                statistic_ids=["light.kitchen"],
                statistic_type="mean",
            )
        with pytest.raises(ValueError):
            instance.statistics_meta_manager.get_many(
                session, statistic_ids={"light.kitchen"}, statistic_source="sensor"
            )
        assert (
            instance.statistics_meta_manager.get_many(
                session,
                statistic_ids={"light.kitchen"},
            )
            == {}
        )


async def test_unsafe_calls_to_statistics_meta_manager(
    async_setup_recorder_instance: RecorderInstanceGenerator, menuai: menuai
) -> None:
    """Test we raise when trying to call non-threadsafe functions on statistics_meta_manager."""
    instance = await async_setup_recorder_instance(
        menuai, {recorder.CONF_COMMIT_INTERVAL: 0}
    )
    with (
        session_scope(session=instance.get_session()) as session,
        pytest.raises(
            RuntimeError, match="Detected unsafe call not in recorder thread"
        ),
    ):
        instance.statistics_meta_manager.delete(
            session,
            statistic_ids=["light.kitchen"],
        )


async def test_invalid_mean_types(
    async_setup_recorder_instance: RecorderInstanceGenerator,
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test passing invalid mean types will be skipped and logged."""
    instance = await async_setup_recorder_instance(
        menuai, {recorder.CONF_COMMIT_INTERVAL: 0}
    )
    instance.recorder_and_worker_thread_ids.add(threading.get_ident())

    valid_metadata: dict[str, tuple[int, StatisticMetaData]] = {
        "sensor.energy": (
            1,
            {
                "mean_type": StatisticMeanType.NONE,
                "has_mean": False,
                "has_sum": True,
                "name": "Total imported energy",
                "source": "recorder",
                "statistic_id": "sensor.energy",
                "unit_of_measurement": "kWh",
            },
        ),
        "sensor.wind_direction": (
            2,
            {
                "mean_type": StatisticMeanType.CIRCULAR,
                "has_mean": False,
                "has_sum": False,
                "name": "Wind direction",
                "source": "recorder",
                "statistic_id": "sensor.wind_direction",
                "unit_of_measurement": DEGREE,
            },
        ),
        "sensor.wind_speed": (
            3,
            {
                "mean_type": StatisticMeanType.ARITHMETIC,
                "has_mean": True,
                "has_sum": False,
                "name": "Wind speed",
                "source": "recorder",
                "statistic_id": "sensor.wind_speed",
                "unit_of_measurement": "km/h",
            },
        ),
    }
    manager = instance.statistics_meta_manager
    with instance.get_session() as session:
        for _, metadata in valid_metadata.values():
            session.add(StatisticsMeta.from_meta(metadata))

        # Add invalid mean type
        session.add(
            StatisticsMeta(
                statistic_id="sensor.invalid",
                source="recorder",
                has_sum=False,
                name="Invalid",
                mean_type=12345,
            )
        )
        session.commit()

        # Check that the invalid mean type was skipped
        assert manager.get_many(session) == valid_metadata
        assert (
            "menuai.components.recorder.table_managers.statistics_meta",
            logging.WARNING,
            "Invalid mean type found for statistic_id: sensor.invalid, mean_type: 12345. Skipping",
        ) in caplog.record_tuples
