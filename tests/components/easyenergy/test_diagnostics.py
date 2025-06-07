"""Tests for the diagnostics data provided by the easyEnergy integration."""

from unittest.mock import MagicMock

from easyenergy import EasyEnergyNoDataError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.menuai import SERVICE_UPDATE_ENTITY
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.mark.freeze_time("2023-01-19 15:00:00")
async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, init_integration)
        == snapshot
    )


@pytest.mark.freeze_time("2023-01-19 15:00:00")
async def test_diagnostics_no_gas_today(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_easyenergy: MagicMock,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics, no gas sensors available."""
    await async_setup_component(menuai, "menuai", {})
    mock_easyenergy.gas_prices.side_effect = EasyEnergyNoDataError

    await menuai.services.async_call(
        "menuai",
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: ["sensor.easyenergy_today_gas_current_hour_price"]},
        blocking=True,
    )
    await menuai.async_block_till_done()

    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, init_integration)
        == snapshot
    )
