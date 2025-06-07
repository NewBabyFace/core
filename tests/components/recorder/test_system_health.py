"""Test recorder system health."""

from unittest.mock import ANY, Mock, patch

import pytest

from menuai.components.recorder import Recorder, get_instance
from menuai.components.recorder.const import SupportedDialect
from menuai.core import menuai
from menuai.setup import async_setup_component

from .common import async_wait_recording_done

from tests.common import get_system_health_info
from tests.typing import RecorderInstanceGenerator


@pytest.mark.skip_on_db_engine(["mysql", "postgresql"])
@pytest.mark.usefixtures("skip_by_db_engine")
async def test_recorder_system_health(
    recorder_mock: Recorder, menuai: menuai, recorder_db_url: str
) -> None:
    """Test recorder system health.

    This test is specific for SQLite.
    """

    assert await async_setup_component(menuai, "system_health", {})
    await async_wait_recording_done(menuai)
    info = await get_system_health_info(menuai, "recorder")
    instance = get_instance(menuai)
    assert info == {
        "current_recorder_run": instance.recorder_runs_manager.current.start,
        "oldest_recorder_run": instance.recorder_runs_manager.first.start,
        "estimated_db_size": ANY,
        "database_engine": SupportedDialect.SQLITE.value,
        "database_version": ANY,
    }


@pytest.mark.parametrize(
    "db_engine", [SupportedDialect.MYSQL, SupportedDialect.POSTGRESQL]
)
async def test_recorder_system_health_alternate_dbms(
    recorder_mock: Recorder,
    menuai: menuai,
    db_engine: SupportedDialect,
    recorder_dialect_name: None,
) -> None:
    """Test recorder system health."""
    assert await async_setup_component(menuai, "system_health", {})
    await async_wait_recording_done(menuai)
    with (
        patch(
            "sqlalchemy.orm.session.Session.execute",
            return_value=Mock(scalar=Mock(return_value=("1048576"))),
        ),
    ):
        info = await get_system_health_info(menuai, "recorder")
    instance = get_instance(menuai)
    assert info == {
        "current_recorder_run": instance.recorder_runs_manager.current.start,
        "oldest_recorder_run": instance.recorder_runs_manager.first.start,
        "estimated_db_size": "1.00 MiB",
        "database_engine": db_engine.value,
        "database_version": ANY,
    }


@pytest.mark.parametrize(
    "db_engine", [SupportedDialect.MYSQL, SupportedDialect.POSTGRESQL]
)
async def test_recorder_system_health_db_url_missing_host(
    recorder_mock: Recorder,
    menuai: menuai,
    db_engine: SupportedDialect,
    recorder_dialect_name: None,
) -> None:
    """Test recorder system health with a db_url without a hostname."""
    assert await async_setup_component(menuai, "system_health", {})
    await async_wait_recording_done(menuai)

    instance = get_instance(menuai)
    with (
        patch.object(
            instance,
            "db_url",
            "postgresql://menuai:blabla@/home_assistant?host=/config/socket",
        ),
        patch(
            "sqlalchemy.orm.session.Session.execute",
            return_value=Mock(scalar=Mock(return_value=("1048576"))),
        ),
    ):
        info = await get_system_health_info(menuai, "recorder")
    assert info == {
        "current_recorder_run": instance.recorder_runs_manager.current.start,
        "oldest_recorder_run": instance.recorder_runs_manager.first.start,
        "estimated_db_size": "1.00 MiB",
        "database_engine": db_engine.value,
        "database_version": ANY,
    }


@pytest.mark.skip_on_db_engine(["mysql", "postgresql"])
@pytest.mark.usefixtures("skip_by_db_engine")
async def test_recorder_system_health_crashed_recorder_runs_table(
    async_setup_recorder_instance: RecorderInstanceGenerator,
    menuai: menuai,
    recorder_db_url: str,
) -> None:
    """Test recorder system health with crashed recorder runs table.

    This test is specific for SQLite.
    """

    with patch(
        "menuai.components.recorder.table_managers.recorder_runs.RecorderRunsManager.load_from_db"
    ):
        assert await async_setup_component(menuai, "system_health", {})
        instance = await async_setup_recorder_instance(menuai)
        await async_wait_recording_done(menuai)
    info = await get_system_health_info(menuai, "recorder")
    assert info == {
        "current_recorder_run": instance.recorder_runs_manager.current.start,
        "oldest_recorder_run": instance.recorder_runs_manager.current.start,
        "estimated_db_size": ANY,
        "database_engine": SupportedDialect.SQLITE.value,
        "database_version": ANY,
    }
