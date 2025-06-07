"""Test Snoo Events."""

from unittest.mock import AsyncMock

from freezegun import freeze_time

from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai

from . import async_init_integration, find_update_callback
from .const import MOCK_SNOO_DATA


@freeze_time("2025-01-01 12:00:00")
async def test_events(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test events and check test values are correctly set."""
    await async_init_integration(menuai)
    assert len(menuai.states.async_all("event")) == 1
    assert menuai.states.get("event.test_snoo_snoo_event").state == STATE_UNAVAILABLE
    find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("event")) == 1
    assert (
        menuai.states.get("event.test_snoo_snoo_event").state
        == "2025-01-01T12:00:00.000+00:00"
    )


@freeze_time("2025-01-01 12:00:00")
async def test_events_data_on_startup(
    menuai: menuai, bypass_api: AsyncMock
) -> None:
    """Test events and check test values are correctly set if data exists on first update."""

    def update_status(_):
        find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)

    bypass_api.get_status.side_effect = update_status
    await async_init_integration(menuai)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("event")) == 1
    assert (
        menuai.states.get("event.test_snoo_snoo_event").state
        == "2025-01-01T12:00:00.000+00:00"
    )
