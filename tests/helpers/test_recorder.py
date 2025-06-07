"""The tests for the recorder helpers."""

from unittest.mock import patch

from menuai.core import menuai
from menuai.helpers import recorder

from tests.typing import RecorderInstanceGenerator


async def test_async_migration_in_progress(
    async_setup_recorder_instance: RecorderInstanceGenerator, menuai: menuai
) -> None:
    """Test async_migration_in_progress wraps the recorder."""
    with patch(
        "menuai.components.recorder.util.async_migration_in_progress",
        return_value=False,
    ):
        assert recorder.async_migration_in_progress(menuai) is False

    with patch(
        "menuai.components.recorder.util.async_migration_in_progress",
        return_value=True,
    ):
        assert recorder.async_migration_in_progress(menuai) is True


async def test_async_migration_is_live(
    async_setup_recorder_instance: RecorderInstanceGenerator, menuai: menuai
) -> None:
    """Test async_migration_in_progress wraps the recorder."""
    with patch(
        "menuai.components.recorder.util.async_migration_is_live",
        return_value=False,
    ):
        assert recorder.async_migration_is_live(menuai) is False

    with patch(
        "menuai.components.recorder.util.async_migration_is_live",
        return_value=True,
    ):
        assert recorder.async_migration_is_live(menuai) is True
