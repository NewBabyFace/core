"""Tests for the sensors provided by the EnergyZero integration."""

from unittest.mock import AsyncMock, MagicMock, patch

from energyzero import EnergyZeroNoDataError
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.energyzero.const import SCAN_INTERVAL
from menuai.const import STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform

pytestmark = [pytest.mark.freeze_time("2022-12-07 15:00:00")]


async def test_sensor(
    menuai: menuai,
    mock_energyzero: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the EnergyZero - Energy sensors."""
    with patch("menuai.components.energyzero.PLATFORMS", ["sensor"]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("init_integration")
async def test_no_gas_today(
    menuai: menuai,
    mock_energyzero: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the EnergyZero - No gas sensors available."""
    mock_energyzero.gas_prices.side_effect = EnergyZeroNoDataError

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get("sensor.energyzero_today_gas_current_hour_price"))
    assert state.state == STATE_UNKNOWN
