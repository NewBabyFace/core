"""Tests for Fritz!Tools sensor platform."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fritzconnection.core.exceptions import FritzConnectionException
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.fritz.const import DOMAIN
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from .const import MOCK_USER_DATA

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.freeze_time(datetime(2024, 9, 1, 20, tzinfo=UTC))
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_setup(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    fc_class_mock,
    fh_class_mock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test setup of Fritz!Tools sensors."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    entry.add_to_menuai(menuai)

    with patch("menuai.components.fritz.PLATFORMS", [Platform.SENSOR]):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_sensor_update_fail(
    menuai: menuai, caplog: pytest.LogCaptureFixture, fc_class_mock, fh_class_mock
) -> None:
    """Test failed update of Fritz!Tools sensors."""

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_DATA)
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    fc_class_mock().call_action_side_effect(FritzConnectionException("Boom"))
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=300))
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "Error while uptaing the data: Boom" in caplog.text

    sensors = menuai.states.async_all(SENSOR_DOMAIN)
    for sensor in sensors:
        assert sensor.state == STATE_UNAVAILABLE
