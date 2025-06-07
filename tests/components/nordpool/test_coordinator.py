"""The test for the Nord Pool coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from pynordpool import (
    NordPoolAuthenticationError,
    NordPoolClient,
    NordPoolEmptyResponseError,
    NordPoolError,
    NordPoolResponseError,
)
import pytest

from menuai.components.nordpool.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai

from . import ENTRY_CONFIG

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.freeze_time("2024-11-05T10:00:00+00:00")
async def test_coordinator(
    menuai: menuai,
    get_client: NordPoolClient,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the Nord Pool coordinator with errors."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
    )

    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    state = menuai.states.get("sensor.nord_pool_se3_current_price")
    assert state.state == "0.92737"

    with (
        patch(
            "menuai.components.nordpool.coordinator.NordPoolClient.async_get_delivery_period",
            side_effect=NordPoolError("error"),
        ) as mock_data,
    ):
        freezer.tick(timedelta(hours=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert mock_data.call_count == 1
        state = menuai.states.get("sensor.nord_pool_se3_current_price")
        assert state.state == STATE_UNAVAILABLE

    with (
        patch(
            "menuai.components.nordpool.coordinator.NordPoolClient.async_get_delivery_period",
            side_effect=NordPoolAuthenticationError("Authentication error"),
        ) as mock_data,
    ):
        assert "Authentication error" not in caplog.text
        freezer.tick(timedelta(hours=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert mock_data.call_count == 1
        state = menuai.states.get("sensor.nord_pool_se3_current_price")
        assert state.state == STATE_UNAVAILABLE
        assert "Authentication error" in caplog.text

    with (
        patch(
            "menuai.components.nordpool.coordinator.NordPoolClient.async_get_delivery_period",
            side_effect=NordPoolEmptyResponseError("Empty response"),
        ) as mock_data,
    ):
        assert "Empty response" not in caplog.text
        freezer.tick(timedelta(hours=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        # Empty responses does not raise
        assert mock_data.call_count == 3
        state = menuai.states.get("sensor.nord_pool_se3_current_price")
        assert state.state == STATE_UNAVAILABLE
        assert "Empty response" in caplog.text

    with (
        patch(
            "menuai.components.nordpool.coordinator.NordPoolClient.async_get_delivery_period",
            side_effect=NordPoolResponseError("Response error"),
        ) as mock_data,
    ):
        assert "Response error" not in caplog.text
        freezer.tick(timedelta(hours=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert mock_data.call_count == 1
        state = menuai.states.get("sensor.nord_pool_se3_current_price")
        assert state.state == STATE_UNAVAILABLE
        assert "Response error" in caplog.text

    freezer.tick(timedelta(hours=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    state = menuai.states.get("sensor.nord_pool_se3_current_price")
    assert state.state == "1.81645"
