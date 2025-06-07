"""Test removing statistics duplicates."""

import importlib
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from menuai.components import recorder
from menuai.components.recorder import statistics
from menuai.components.recorder.auto_repairs.statistics.duplicates import (
    delete_statistics_duplicates,
    delete_statistics_meta_duplicates,
)
from menuai.components.recorder.statistics import async_add_external_statistics
from menuai.components.recorder.util import session_scope
from menuai.core import menuai
from menuai.util import dt as dt_util

from ...common import async_wait_recording_done

from tests.common import async_test_home_assistant
from tests.typing import RecorderInstanceContextManager


@pytest.fixture
async def mock_recorder_before_menuai(
    async_test_recorder: RecorderInstanceContextManager,
) -> None:
    """Set up recorder."""


@pytest.mark.usefixtures("recorder_mock")
async def test_delete_duplicates_no_duplicates(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test removal of duplicated statistics."""
    await async_wait_recording_done(menuai)
    instance = recorder.get_instance(menuai)
    with session_scope(menuai=menuai) as session:
        delete_statistics_duplicates(instance, menuai, session)
    assert "duplicated statistics rows" not in caplog.text
    assert "Found non identical" not in caplog.text
    assert "Found duplicated" not in caplog.text


@pytest.mark.usefixtures("recorder_mock")
async def test_duplicate_statistics_handle_integrity_error(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the recorder does not blow up if statistics is duplicated."""
    await async_wait_recording_done(menuai)

    period1 = dt_util.as_utc(dt_util.parse_datetime("2021-09-01 00:00:00"))
    period2 = dt_util.as_utc(dt_util.parse_datetime("2021-09-30 23:00:00"))

    external_energy_metadata_1 = {
        "has_mean": False,
        "has_sum": True,
        "name": "Total imported energy",
        "source": "test",
        "statistic_id": "test:total_energy_import_tariff_1",
        "unit_of_measurement": "kWh",
    }
    external_energy_statistics_1 = [
        {
            "start": period1,
            "last_reset": None,
            "state": 3,
            "sum": 5,
        },
    ]
    external_energy_statistics_2 = [
        {
            "start": period2,
            "last_reset": None,
            "state": 3,
            "sum": 6,
        }
    ]

    with (
        patch.object(statistics, "_statistics_exists", return_value=False),
        patch.object(
            statistics, "_insert_statistics", wraps=statistics._insert_statistics
        ) as insert_statistics_mock,
    ):
        async_add_external_statistics(
            menuai, external_energy_metadata_1, external_energy_statistics_1
        )
        async_add_external_statistics(
            menuai, external_energy_metadata_1, external_energy_statistics_1
        )
        async_add_external_statistics(
            menuai, external_energy_metadata_1, external_energy_statistics_2
        )
        await async_wait_recording_done(menuai)
        assert insert_statistics_mock.call_count == 3

    with session_scope(menuai=menuai) as session:
        tmp = session.query(recorder.db_schema.Statistics).all()
        assert len(tmp) == 2

    assert "Blocked attempt to insert duplicated statistic rows" in caplog.text


def _create_engine_28(*args, **kwargs):
    """Test version of create_engine that initializes with old schema.

    This simulates an existing db with the old schema.
    """
    module = "tests.components.recorder.db_schema_28"
    importlib.import_module(module)
    old_db_schema = sys.modules[module]
    engine = create_engine(*args, **kwargs)
    old_db_schema.Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            recorder.db_schema.StatisticsRuns(start=statistics.get_start_time())
        )
        session.add(
            recorder.db_schema.SchemaChanges(
                schema_version=old_db_schema.SCHEMA_VERSION
            )
        )
        session.commit()
    return engine


@pytest.mark.parametrize("persistent_database", [True])
@pytest.mark.usefixtures("menuai_storage")  # Prevent test menuai from writing to storage
async def test_delete_metadata_duplicates(
    async_test_recorder: RecorderInstanceContextManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test removal of duplicated statistics."""
    module = "tests.components.recorder.db_schema_28"
    importlib.import_module(module)
    old_db_schema = sys.modules[module]

    external_energy_metadata_1 = {
        "has_mean": False,
        "has_sum": True,
        "name": "Total imported energy",
        "source": "test",
        "statistic_id": "test:total_energy_import_tariff_1",
        "unit_of_measurement": "kWh",
    }
    external_energy_metadata_2 = {
        "has_mean": False,
        "has_sum": True,
        "name": "Total imported energy",
        "source": "test",
        "statistic_id": "test:total_energy_import_tariff_1",
        "unit_of_measurement": "kWh",
    }
    external_co2_metadata = {
        "has_mean": True,
        "has_sum": False,
        "name": "Fossil percentage",
        "source": "test",
        "statistic_id": "test:fossil_percentage",
        "unit_of_measurement": "%",
    }

    def add_statistics_meta(menuai: menuai) -> None:
        with session_scope(menuai=menuai) as session:
            session.add(
                recorder.db_schema.StatisticsMeta.from_meta(external_energy_metadata_1)
            )
            session.add(
                recorder.db_schema.StatisticsMeta.from_meta(external_energy_metadata_2)
            )
            session.add(
                recorder.db_schema.StatisticsMeta.from_meta(external_co2_metadata)
            )

    def get_statistics_meta(menuai: menuai) -> list:
        with session_scope(menuai=menuai, read_only=True) as session:
            return list(session.query(recorder.db_schema.StatisticsMeta).all())

    # Create some duplicated statistics_meta with schema version 28
    with (
        patch.object(recorder, "db_schema", old_db_schema),
        patch.object(
            recorder.migration, "SCHEMA_VERSION", old_db_schema.SCHEMA_VERSION
        ),
        patch.object(
            recorder.migration, "non_live_data_migration_needed", return_value=False
        ),
        patch(
            "menuai.components.recorder.core.create_engine",
            new=_create_engine_28,
        ),
    ):
        async with (
            async_test_home_assistant() as menuai,
            async_test_recorder(menuai),
        ):
            await async_wait_recording_done(menuai)
            await async_wait_recording_done(menuai)

            instance = recorder.get_instance(menuai)
            await instance.async_add_executor_job(add_statistics_meta, menuai)

            tmp = await instance.async_add_executor_job(get_statistics_meta, menuai)
            assert len(tmp) == 3
            assert tmp[0].id == 1
            assert tmp[0].statistic_id == "test:total_energy_import_tariff_1"
            assert tmp[1].id == 2
            assert tmp[1].statistic_id == "test:total_energy_import_tariff_1"
            assert tmp[2].id == 3
            assert tmp[2].statistic_id == "test:fossil_percentage"

            await menuai.async_stop()

    # Test that the duplicates are removed during migration from schema 28
    async with (
        async_test_home_assistant() as menuai,
        async_test_recorder(menuai),
    ):
        await menuai.async_start()
        await async_wait_recording_done(menuai)
        await async_wait_recording_done(menuai)

        assert "Deleted 1 duplicated statistics_meta rows" in caplog.text
        instance = recorder.get_instance(menuai)
        tmp = await instance.async_add_executor_job(get_statistics_meta, menuai)
        assert len(tmp) == 2
        assert tmp[0].id == 2
        assert tmp[0].statistic_id == "test:total_energy_import_tariff_1"
        assert tmp[1].id == 3
        assert tmp[1].statistic_id == "test:fossil_percentage"

        await menuai.async_stop()


@pytest.mark.parametrize("persistent_database", [True])
@pytest.mark.usefixtures("menuai_storage")  # Prevent test menuai from writing to storage
async def test_delete_metadata_duplicates_many(
    async_test_recorder: RecorderInstanceContextManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test removal of duplicated statistics."""
    module = "tests.components.recorder.db_schema_28"
    importlib.import_module(module)
    old_db_schema = sys.modules[module]

    external_energy_metadata_1 = {
        "has_mean": False,
        "has_sum": True,
        "name": "Total imported energy",
        "source": "test",
        "statistic_id": "test:total_energy_import_tariff_1",
        "unit_of_measurement": "kWh",
    }
    external_energy_metadata_2 = {
        "has_mean": False,
        "has_sum": True,
        "name": "Total imported energy",
        "source": "test",
        "statistic_id": "test:total_energy_import_tariff_2",
        "unit_of_measurement": "kWh",
    }
    external_co2_metadata = {
        "has_mean": True,
        "has_sum": False,
        "name": "Fossil percentage",
        "source": "test",
        "statistic_id": "test:fossil_percentage",
        "unit_of_measurement": "%",
    }

    def add_statistics_meta(menuai: menuai) -> None:
        with session_scope(menuai=menuai) as session:
            session.add(
                recorder.db_schema.StatisticsMeta.from_meta(external_energy_metadata_1)
            )
            for _ in range(1100):
                session.add(
                    recorder.db_schema.StatisticsMeta.from_meta(
                        external_energy_metadata_1
                    )
                )
            session.add(
                recorder.db_schema.StatisticsMeta.from_meta(external_energy_metadata_2)
            )
            session.add(
                recorder.db_schema.StatisticsMeta.from_meta(external_energy_metadata_2)
            )
            session.add(
                recorder.db_schema.StatisticsMeta.from_meta(external_co2_metadata)
            )
            session.add(
                recorder.db_schema.StatisticsMeta.from_meta(external_co2_metadata)
            )

    def get_statistics_meta(menuai: menuai) -> list:
        with session_scope(menuai=menuai, read_only=True) as session:
            return list(session.query(recorder.db_schema.StatisticsMeta).all())

    # Create some duplicated statistics with schema version 28
    with (
        patch.object(recorder, "db_schema", old_db_schema),
        patch.object(
            recorder.migration, "SCHEMA_VERSION", old_db_schema.SCHEMA_VERSION
        ),
        patch.object(
            recorder.migration, "non_live_data_migration_needed", return_value=False
        ),
        patch(
            "menuai.components.recorder.core.create_engine",
            new=_create_engine_28,
        ),
    ):
        async with (
            async_test_home_assistant() as menuai,
            async_test_recorder(menuai),
        ):
            await async_wait_recording_done(menuai)
            await async_wait_recording_done(menuai)

            instance = recorder.get_instance(menuai)
            await instance.async_add_executor_job(add_statistics_meta, menuai)

            await menuai.async_stop()

    # Test that the duplicates are removed during migration from schema 28
    async with (
        async_test_home_assistant() as menuai,
        async_test_recorder(menuai),
    ):
        await menuai.async_start()
        await async_wait_recording_done(menuai)
        await async_wait_recording_done(menuai)

        assert "Deleted 1102 duplicated statistics_meta rows" in caplog.text
        instance = recorder.get_instance(menuai)
        tmp = await instance.async_add_executor_job(get_statistics_meta, menuai)
        assert len(tmp) == 3
        assert tmp[0].id == 1101
        assert tmp[0].statistic_id == "test:total_energy_import_tariff_1"
        assert tmp[1].id == 1103
        assert tmp[1].statistic_id == "test:total_energy_import_tariff_2"
        assert tmp[2].id == 1105
        assert tmp[2].statistic_id == "test:fossil_percentage"

        await menuai.async_stop()


@pytest.mark.usefixtures("recorder_mock")
async def test_delete_metadata_duplicates_no_duplicates(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test removal of duplicated statistics."""
    await async_wait_recording_done(menuai)
    with session_scope(menuai=menuai) as session:
        instance = recorder.get_instance(menuai)
        delete_statistics_meta_duplicates(instance, session)
    assert "duplicated statistics_meta rows" not in caplog.text
