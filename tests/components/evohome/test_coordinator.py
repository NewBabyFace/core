"""The tests for the evohome coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from evohomeasync2 import EvohomeClient
from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.evohome import EvoData
from menuai.components.evohome.const import DOMAIN
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers.update_coordinator import UpdateFailed

from tests.common import async_fire_time_changed


@pytest.mark.parametrize("install", ["minimal"])
async def test_setup_platform(
    menuai: menuai,
    config: dict[str, str],
    evohome: EvohomeClient,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test entities and their states after setup of evohome."""

    evo_data: EvoData = menuai.data.get(DOMAIN)  # type: ignore[assignment]
    update_interval: timedelta = evo_data.coordinator.update_interval  # type: ignore[assignment]

    # confirm initial state after coordinator.async_first_refresh()...
    state = menuai.states.get("climate.my_home")
    assert state is not None and state.state != STATE_UNAVAILABLE

    with patch(
        "menuai.components.evohome.coordinator.EvoDataUpdateCoordinator._async_update_data",
        side_effect=UpdateFailed,
    ):
        freezer.tick(update_interval)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    # confirm appropriate response to loss of state...
    state = menuai.states.get("climate.my_home")
    assert state is not None and state.state == STATE_UNAVAILABLE

    freezer.tick(update_interval)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    # if coordinator is working, the state will be restored
    state = menuai.states.get("climate.my_home")
    assert state is not None and state.state != STATE_UNAVAILABLE
