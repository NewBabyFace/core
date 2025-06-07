"""Tests for the Backup integration."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.backup.const import DOMAIN
from menuai.core import menuai

from .common import setup_backup_integration

from tests.typing import WebSocketGenerator


@pytest.fixture(autouse=True)
def mock_delay_save() -> Generator[None]:
    """Mock the delay save constant."""
    with patch("menuai.components.backup.store.STORE_DELAY_SAVE", 0):
        yield


@pytest.mark.parametrize(
    "store_data",
    [
        {
            "data": {
                "backups": [
                    {
                        "backup_id": "abc123",
                        "failed_agent_ids": ["test.remote"],
                    }
                ],
                "config": {
                    "create_backup": {
                        "agent_ids": [],
                        "include_addons": None,
                        "include_all_addons": False,
                        "include_database": True,
                        "include_folders": None,
                        "name": None,
                        "password": None,
                    },
                    "last_attempted_automatic_backup": None,
                    "last_completed_automatic_backup": None,
                    "retention": {
                        "copies": None,
                        "days": None,
                    },
                    "schedule": {
                        "state": "never",
                    },
                },
            },
            "key": DOMAIN,
            "version": 1,
        },
        {
            "data": {
                "backups": [
                    {
                        "backup_id": "abc123",
                        "failed_agent_ids": ["test.remote"],
                    }
                ],
                "config": {
                    "create_backup": {
                        "agent_ids": [],
                        "include_addons": None,
                        "include_all_addons": False,
                        "include_database": True,
                        "include_folders": None,
                        "name": None,
                        "password": None,
                    },
                    "last_attempted_automatic_backup": None,
                    "last_completed_automatic_backup": None,
                    "retention": {
                        "copies": 0,
                        "days": 0,
                    },
                    "schedule": {
                        "state": "never",
                    },
                },
            },
            "key": DOMAIN,
            "version": 1,
        },
        {
            "data": {
                "backups": [
                    {
                        "backup_id": "abc123",
                        "failed_addons": [
                            {
                                "name": "Test add-on",
                                "slug": "test_addon",
                                "version": "1.0.0",
                            }
                        ],
                        "failed_agent_ids": ["test.remote"],
                        "failed_folders": ["ssl"],
                    }
                ],
                "config": {
                    "agents": {"test.remote": {"protected": True, "retention": None}},
                    "automatic_backups_configured": False,
                    "create_backup": {
                        "agent_ids": [],
                        "include_addons": None,
                        "include_all_addons": False,
                        "include_database": True,
                        "include_folders": None,
                        "name": None,
                        "password": None,
                    },
                    "last_attempted_automatic_backup": None,
                    "last_completed_automatic_backup": None,
                    "retention": {
                        "copies": None,
                        "days": None,
                    },
                    "schedule": {
                        "days": [],
                        "recurrence": "never",
                        "time": None,
                    },
                    "something_from_the_future": "value",
                },
            },
            "key": DOMAIN,
            "version": 2,
        },
        {
            "data": {
                "backups": [
                    {
                        "backup_id": "abc123",
                        "failed_agent_ids": ["test.remote"],
                    }
                ],
                "config": {
                    "agents": {"test.remote": {"protected": True}},
                    "create_backup": {
                        "agent_ids": [],
                        "include_addons": None,
                        "include_all_addons": False,
                        "include_database": True,
                        "include_folders": None,
                        "name": None,
                        "password": None,
                    },
                    "last_attempted_automatic_backup": None,
                    "last_completed_automatic_backup": None,
                    "retention": {
                        "copies": None,
                        "days": None,
                    },
                    "schedule": {
                        "days": [],
                        "recurrence": "never",
                        "state": "never",
                        "time": None,
                    },
                },
            },
            "key": DOMAIN,
            "minor_version": 4,
            "version": 1,
        },
        {
            "data": {
                "backups": [
                    {
                        "backup_id": "abc123",
                        "failed_agent_ids": ["test.remote"],
                    }
                ],
                "config": {
                    "agents": {"test.remote": {"protected": True}},
                    "create_backup": {
                        "agent_ids": [],
                        "include_addons": None,
                        "include_all_addons": False,
                        "include_database": True,
                        "include_folders": None,
                        "name": None,
                        "password": "hunter2",
                    },
                    "last_attempted_automatic_backup": None,
                    "last_completed_automatic_backup": None,
                    "retention": {
                        "copies": None,
                        "days": None,
                    },
                    "schedule": {
                        "days": [],
                        "recurrence": "never",
                        "state": "never",
                        "time": None,
                    },
                },
            },
            "key": DOMAIN,
            "minor_version": 4,
            "version": 1,
        },
        {
            "data": {
                "backups": [
                    {
                        "backup_id": "abc123",
                        "failed_agent_ids": ["test.remote"],
                    }
                ],
                "config": {
                    "agents": {
                        "test.remote": {
                            "protected": True,
                            "retention": {"copies": None, "days": None},
                        }
                    },
                    "automatic_backups_configured": True,
                    "create_backup": {
                        "agent_ids": [],
                        "include_addons": None,
                        "include_all_addons": False,
                        "include_database": True,
                        "include_folders": None,
                        "name": None,
                        "password": "hunter2",
                    },
                    "last_attempted_automatic_backup": None,
                    "last_completed_automatic_backup": None,
                    "retention": {
                        "copies": None,
                        "days": None,
                    },
                    "schedule": {
                        "days": [],
                        "recurrence": "never",
                        "state": "never",
                        "time": None,
                    },
                },
            },
            "key": DOMAIN,
            "minor_version": 6,
            "version": 1,
        },
        {
            "data": {
                "backups": [
                    {
                        "backup_id": "abc123",
                        "failed_addons": [
                            {
                                "name": "Test add-on",
                                "slug": "test_addon",
                                "version": "1.0.0",
                            }
                        ],
                        "failed_agent_ids": ["test.remote"],
                        "failed_folders": ["ssl"],
                    }
                ],
                "config": {
                    "agents": {
                        "test.remote": {
                            "protected": True,
                            "retention": {"copies": None, "days": None},
                        }
                    },
                    "automatic_backups_configured": True,
                    "create_backup": {
                        "agent_ids": [],
                        "include_addons": None,
                        "include_all_addons": False,
                        "include_database": True,
                        "include_folders": None,
                        "name": None,
                        "password": "hunter2",
                    },
                    "last_attempted_automatic_backup": None,
                    "last_completed_automatic_backup": None,
                    "retention": {
                        "copies": None,
                        "days": None,
                    },
                    "schedule": {
                        "days": [],
                        "recurrence": "never",
                        "state": "never",
                        "time": None,
                    },
                },
            },
            "key": DOMAIN,
            "minor_version": 7,
            "version": 1,
        },
    ],
)
async def test_store_migration(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    menuai_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
    store_data: dict[str, Any],
) -> None:
    """Test migrating the backup store."""
    menuai_storage[DOMAIN] = store_data
    await setup_backup_integration(menuai)
    await menuai.async_block_till_done()

    # Check migrated data
    assert menuai_storage[DOMAIN] == snapshot

    # Update settings, then check saved data
    client = await menuai_ws_client(menuai)
    await client.send_json_auto_id(
        {
            "type": "backup/config/update",
            "create_backup": {"agent_ids": ["test-agent"]},
        }
    )
    result = await client.receive_json()
    assert result["success"]
    await menuai.async_block_till_done()
    assert menuai_storage[DOMAIN] == snapshot
