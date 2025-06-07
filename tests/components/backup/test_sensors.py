"""Tests for the sensors of the Backup integration."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.backup import store
from menuai.components.backup.const import DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import setup_backup_integration

from tests.common import async_fire_time_changed, snapshot_platform
from tests.typing import WebSocketGenerator


@pytest.mark.usefixtures("mock_backup_generation")
async def test_sensors(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test setup of backup sensors."""
    with patch("menuai.components.backup.PLATFORMS", [Platform.SENSOR]):
        await setup_backup_integration(menuai, with_menuaiio=False)
        await menuai.async_block_till_done(wait_background_tasks=True)

    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)

    # start backup and check sensor states again
    client = await menuai_ws_client(menuai)
    await menuai.async_block_till_done()
    await client.send_json_auto_id(
        {"type": "backup/generate", "agent_ids": ["backup.local"]}
    )

    assert await client.receive_json()
    state = menuai.states.get("sensor.backup_backup_manager_state")
    assert state.state == "create_backup"

    await menuai.async_block_till_done(wait_background_tasks=True)
    state = menuai.states.get("sensor.backup_backup_manager_state")
    assert state.state == "idle"


async def test_sensor_updates(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
    menuai_storage: dict[str, Any],
    create_backup: AsyncMock,
) -> None:
    """Test update of backup sensors."""
    # Ensure created backup is already protected,
    # to avoid manager creating a new EncryptedBackupStreamer
    # instead of using the already mocked stream writer.
    created_backup: MagicMock = create_backup.return_value[1].result().backup
    created_backup.protected = True

    await menuai.config.async_set_time_zone("Europe/Amsterdam")
    freezer.move_to("2024-11-12T12:00:00+01:00")
    storage_data = {
        "backups": [],
        "config": {
            "agents": {},
            "automatic_backups_configured": True,
            "create_backup": {
                "agent_ids": ["test.remote"],
                "include_addons": [],
                "include_all_addons": False,
                "include_database": True,
                "include_folders": [],
                "name": "test-name",
                "password": "test-password",
            },
            "retention": {"copies": None, "days": None},
            "last_attempted_automatic_backup": "2024-11-11T04:45:00+01:00",
            "last_completed_automatic_backup": "2024-11-11T04:45:00+01:00",
            "schedule": {
                "days": [],
                "recurrence": "daily",
                "state": "never",
                "time": "06:00",
            },
        },
    }
    menuai_storage[DOMAIN] = {
        "data": storage_data,
        "key": DOMAIN,
        "version": store.STORAGE_VERSION,
        "minor_version": store.STORAGE_VERSION_MINOR,
    }

    with patch("menuai.components.backup.PLATFORMS", [Platform.SENSOR]):
        await setup_backup_integration(
            menuai, with_menuaiio=False, remote_agents=["test.remote"]
        )
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("sensor.backup_last_attempted_automatic_backup")
    assert state.state == "2024-11-11T03:45:00+00:00"
    state = menuai.states.get("sensor.backup_last_successful_automatic_backup")
    assert state.state == "2024-11-11T03:45:00+00:00"
    state = menuai.states.get("sensor.backup_next_scheduled_automatic_backup")
    assert state.state == "2024-11-13T05:00:00+00:00"

    freezer.move_to("2024-11-13T12:00:00+01:00")
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.backup_last_attempted_automatic_backup")
    assert state.state == "2024-11-13T11:00:00+00:00"
    state = menuai.states.get("sensor.backup_last_successful_automatic_backup")
    assert state.state == "2024-11-13T11:00:00+00:00"
    state = menuai.states.get("sensor.backup_next_scheduled_automatic_backup")
    assert state.state == "2024-11-14T05:00:00+00:00"
