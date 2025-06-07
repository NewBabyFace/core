"""Test backup platform for the Recorder integration."""

from contextlib import AbstractContextManager, nullcontext as does_not_raise
from unittest.mock import patch

import pytest

from menuai.components.recorder import Recorder
from menuai.components.recorder.backup import async_post_backup, async_pre_backup
from menuai.core import CoreState, menuai
from menuai.exceptions import menuaiError


async def test_async_pre_backup(recorder_mock: Recorder, menuai: menuai) -> None:
    """Test pre backup."""
    with patch(
        "menuai.components.recorder.core.Recorder.lock_database"
    ) as lock_mock:
        await async_pre_backup(menuai)
    assert lock_mock.called


RAISES_menuai_NOT_RUNNING = pytest.raises(
    menuaiError, match="MenuAI is not running"
)


@pytest.mark.parametrize(
    ("core_state", "expected_result", "lock_calls"),
    [
        (CoreState.final_write, RAISES_menuai_NOT_RUNNING, 0),
        (CoreState.not_running, RAISES_menuai_NOT_RUNNING, 0),
        (CoreState.running, does_not_raise(), 1),
        (CoreState.starting, RAISES_menuai_NOT_RUNNING, 0),
        (CoreState.stopped, RAISES_menuai_NOT_RUNNING, 0),
        (CoreState.stopping, RAISES_menuai_NOT_RUNNING, 0),
    ],
)
async def test_async_pre_backup_core_state(
    recorder_mock: Recorder,
    menuai: menuai,
    core_state: CoreState,
    expected_result: AbstractContextManager,
    lock_calls: int,
) -> None:
    """Test pre backup in different core states."""
    menuai.set_state(core_state)
    with (  # pylint: disable=confusing-with-statement
        patch(
            "menuai.components.recorder.core.Recorder.lock_database"
        ) as lock_mock,
        expected_result,
    ):
        await async_pre_backup(menuai)
    assert len(lock_mock.mock_calls) == lock_calls


async def test_async_pre_backup_with_timeout(
    recorder_mock: Recorder, menuai: menuai
) -> None:
    """Test pre backup with timeout."""
    with (
        patch(
            "menuai.components.recorder.core.Recorder.lock_database",
            side_effect=TimeoutError(),
        ) as lock_mock,
        pytest.raises(TimeoutError),
    ):
        await async_pre_backup(menuai)
    assert lock_mock.called


async def test_async_pre_backup_with_migration(
    recorder_mock: Recorder, menuai: menuai
) -> None:
    """Test pre backup with migration."""
    with (
        patch(
            "menuai.components.recorder.core.Recorder.lock_database"
        ) as lock_mock,
        patch(
            "menuai.components.recorder.backup.async_migration_in_progress",
            return_value=True,
        ),
        pytest.raises(menuaiError, match="Database migration in progress"),
    ):
        await async_pre_backup(menuai)
    assert not lock_mock.called


async def test_async_post_backup(recorder_mock: Recorder, menuai: menuai) -> None:
    """Test post backup."""
    with patch(
        "menuai.components.recorder.core.Recorder.unlock_database"
    ) as unlock_mock:
        await async_post_backup(menuai)
    assert unlock_mock.called


async def test_async_post_backup_failure(
    recorder_mock: Recorder, menuai: menuai
) -> None:
    """Test post backup failure."""
    with (
        patch(
            "menuai.components.recorder.core.Recorder.unlock_database",
            return_value=False,
        ) as unlock_mock,
        pytest.raises(
            menuaiError, match="Could not release database write lock"
        ),
    ):
        await async_post_backup(menuai)
    assert unlock_mock.called
