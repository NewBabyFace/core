"""Tests for the registry."""

from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.core import CoreState, menuai
from menuai.helpers import storage
from menuai.helpers.registry import SAVE_DELAY, SAVE_DELAY_LONG, BaseRegistry

from tests.common import async_fire_time_changed


class SampleRegistry(BaseRegistry):
    """Class to hold a registry of X."""

    def __init__(self, menuai: menuai) -> None:
        """Initialize the registry."""
        self.menuai = menuai
        self._store = storage.Store(menuai, 1, "test")
        self.save_calls = 0

    def _data_to_save(self) -> dict[str, Any]:
        """Return data of registry to save."""
        self.save_calls += 1
        return {}


@pytest.mark.parametrize(
    "long_delay_state",
    [
        CoreState.not_running,
        CoreState.starting,
        CoreState.stopped,
        CoreState.final_write,
    ],
)
async def test_async_schedule_save(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    long_delay_state: CoreState,
    menuai_storage: dict[str, Any],
) -> None:
    """Test saving the registry.

    If CoreState is not running, it should save with long delay.

    Storage will always save at final write if there is a
    write pending so we should not schedule a save in that case.
    """
    registry = SampleRegistry(menuai)
    menuai.set_state(long_delay_state)

    registry.async_schedule_save()
    freezer.tick(SAVE_DELAY)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert registry.save_calls == 0

    freezer.tick(SAVE_DELAY_LONG)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert registry.save_calls == 1

    menuai.set_state(CoreState.running)
    registry.async_schedule_save()
    freezer.tick(SAVE_DELAY)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert registry.save_calls == 2
