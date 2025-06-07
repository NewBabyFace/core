"""Tests for the Amazon Devices notify platform."""

from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.amazon_devices.coordinator import SCAN_INTERVAL
from menuai.components.notify import (
    ATTR_MESSAGE,
    DOMAIN as NOTIFY_DOMAIN,
    SERVICE_SEND_MESSAGE,
)
from menuai.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import setup_integration
from .const import TEST_SERIAL_NUMBER

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_amazon_devices_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.amazon_devices.PLATFORMS", [Platform.NOTIFY]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    "mode",
    ["speak", "announce"],
)
async def test_notify_send_message(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_amazon_devices_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    mode: str,
) -> None:
    """Test notify send message."""
    await setup_integration(menuai, mock_config_entry)

    entity_id = f"notify.echo_test_{mode}"

    now = dt_util.parse_datetime("2021-01-09 12:00:00+00:00")
    assert now

    freezer.move_to(now)
    await menuai.services.async_call(
        NOTIFY_DOMAIN,
        SERVICE_SEND_MESSAGE,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_MESSAGE: "Test Message",
        },
        blocking=True,
    )

    assert (state := menuai.states.get(entity_id))
    assert state.state == now.isoformat()


async def test_offline_device(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_amazon_devices_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test offline device handling."""

    entity_id = "notify.echo_test_announce"

    mock_amazon_devices_client.get_devices_data.return_value[
        TEST_SERIAL_NUMBER
    ].online = False

    await setup_integration(menuai, mock_config_entry)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_UNAVAILABLE

    mock_amazon_devices_client.get_devices_data.return_value[
        TEST_SERIAL_NUMBER
    ].online = True

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state != STATE_UNAVAILABLE
