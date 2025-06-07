"""Tests for the AirGradient number platform."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from airgradient import AirGradientConnectionError, AirGradientError, Config
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.airgradient.const import DOMAIN
from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_load_fixture,
    snapshot_platform,
)


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_airgradient_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.airgradient.PLATFORMS", [Platform.NUMBER]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_setting_value(
    menuai: menuai,
    mock_airgradient_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting value."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        service_data={ATTR_VALUE: 50},
        target={ATTR_ENTITY_ID: "number.airgradient_display_brightness"},
        blocking=True,
    )
    mock_airgradient_client.set_display_brightness.assert_called_once()

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        service_data={ATTR_VALUE: 50},
        target={ATTR_ENTITY_ID: "number.airgradient_led_bar_brightness"},
        blocking=True,
    )
    mock_airgradient_client.set_led_bar_brightness.assert_called_once()


async def test_cloud_creates_no_number(
    menuai: menuai,
    mock_cloud_airgradient_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test cloud configuration control."""
    with patch("menuai.components.airgradient.PLATFORMS", [Platform.NUMBER]):
        await setup_integration(menuai, mock_config_entry)

    assert len(menuai.states.async_all()) == 0

    mock_cloud_airgradient_client.get_config.return_value = Config.from_json(
        await async_load_fixture(menuai, "get_config_local.json", DOMAIN)
    )

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 2

    mock_cloud_airgradient_client.get_config.return_value = Config.from_json(
        await async_load_fixture(menuai, "get_config_cloud.json", DOMAIN)
    )

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0


@pytest.mark.parametrize(
    ("exception", "error_message"),
    [
        (
            AirGradientConnectionError("Something happened"),
            "An error occurred while communicating with the Airgradient device: Something happened",
        ),
        (
            AirGradientError("Something else happened"),
            "An unknown error occurred while communicating with the Airgradient device: Something else happened",
        ),
    ],
)
async def test_exception_handling(
    menuai: menuai,
    mock_airgradient_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    exception: Exception,
    error_message: str,
) -> None:
    """Test exception handling."""
    await setup_integration(menuai, mock_config_entry)

    mock_airgradient_client.set_display_brightness.side_effect = exception
    with pytest.raises(menuaiError, match=error_message):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            service_data={ATTR_VALUE: 50},
            target={ATTR_ENTITY_ID: "number.airgradient_display_brightness"},
            blocking=True,
        )
