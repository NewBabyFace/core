"""Test the backups for WebDAV."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from io import StringIO
from unittest.mock import Mock, patch

from aiowebdav2.exceptions import UnauthorizedError, WebDavError
import pytest

from menuai.components.backup import DOMAIN as BACKUP_DOMAIN, AgentBackup
from menuai.components.webdav.backup import async_register_backup_agents_listener
from menuai.components.webdav.const import DATA_BACKUP_AGENT_LISTENERS, DOMAIN
from menuai.core import menuai
from menuai.helpers.backup import async_initialize_backup
from menuai.setup import async_setup_component

from .const import BACKUP_METADATA

from tests.common import AsyncMock, MockConfigEntry
from tests.typing import ClientSessionGenerator, WebSocketGenerator


@pytest.fixture(autouse=True)
async def setup_backup_integration(
    menuai: menuai, mock_config_entry: MockConfigEntry, webdav_client: AsyncMock
) -> AsyncGenerator[None]:
    """Set up webdav integration."""
    with (
        patch("menuai.components.backup.is_menuaiio", return_value=False),
        patch("menuai.components.backup.store.STORE_DELAY_SAVE", 0),
    ):
        async_initialize_backup(menuai)
        assert await async_setup_component(menuai, BACKUP_DOMAIN, {})
        mock_config_entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

        yield


async def test_agents_info(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test backup agent info."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agents": [
            {"agent_id": "backup.local", "name": "local"},
            {
                "agent_id": f"{DOMAIN}.{mock_config_entry.entry_id}",
                "name": mock_config_entry.title,
            },
        ],
    }


async def test_agents_list_backups(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test agent list backups."""

    client = await menuai_ws_client(menuai)
    await client.send_json_auto_id({"type": "backup/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"]["agent_errors"] == {}
    assert response["result"]["backups"] == [
        {
            "addons": [],
            "agents": {
                "webdav.01JKXV07ASC62D620DGYNG2R8H": {
                    "protected": False,
                    "size": 34519040,
                }
            },
            "backup_id": "23e64aec",
            "database_included": True,
            "date": "2025-02-10T17:47:22.727189+01:00",
            "extra_metadata": {},
            "failed_addons": [],
            "failed_agent_ids": [],
            "failed_folders": [],
            "folders": [],
            "menuai_included": True,
            "menuai_version": "2025.2.1",
            "name": "Automatic backup 2025.2.1",
            "with_automatic_settings": None,
        }
    ]


async def test_agents_get_backup(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test agent get backup."""

    backup_id = BACKUP_METADATA["backup_id"]
    client = await menuai_ws_client(menuai)
    await client.send_json_auto_id({"type": "backup/details", "backup_id": backup_id})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"]["agent_errors"] == {}
    assert response["result"]["backup"] == {
        "addons": [],
        "agents": {
            f"{DOMAIN}.{mock_config_entry.entry_id}": {
                "protected": False,
                "size": 34519040,
            }
        },
        "backup_id": "23e64aec",
        "database_included": True,
        "date": "2025-02-10T17:47:22.727189+01:00",
        "extra_metadata": {},
        "failed_addons": [],
        "failed_agent_ids": [],
        "failed_folders": [],
        "folders": [],
        "menuai_included": True,
        "menuai_version": "2025.2.1",
        "name": "Automatic backup 2025.2.1",
        "with_automatic_settings": None,
    }


async def test_agents_delete(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    webdav_client: AsyncMock,
) -> None:
    """Test agent delete backup."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {
            "type": "backup/delete",
            "backup_id": BACKUP_METADATA["backup_id"],
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"agent_errors": {}}
    assert webdav_client.clean.call_count == 2


async def test_agents_upload(
    menuai_client: ClientSessionGenerator,
    webdav_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test agent upload backup."""
    client = await menuai_client()
    test_backup = AgentBackup.from_dict(BACKUP_METADATA)

    with (
        patch(
            "menuai.components.backup.manager.BackupManager.async_get_backup",
        ) as fetch_backup,
        patch(
            "menuai.components.backup.manager.read_backup",
            return_value=test_backup,
        ),
        patch("pathlib.Path.open") as mocked_open,
    ):
        mocked_open.return_value.read = Mock(side_effect=[b"test", b""])
        fetch_backup.return_value = test_backup
        resp = await client.post(
            f"/api/backup/upload?agent_id={DOMAIN}.{mock_config_entry.entry_id}",
            data={"file": StringIO("test")},
        )

    assert resp.status == 201
    assert webdav_client.upload_iter.call_count == 2


async def test_agents_download(
    menuai_client: ClientSessionGenerator,
    webdav_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test agent download backup."""
    client = await menuai_client()
    backup_id = BACKUP_METADATA["backup_id"]

    resp = await client.get(
        f"/api/backup/download/{backup_id}?agent_id={DOMAIN}.{mock_config_entry.entry_id}"
    )
    assert resp.status == 200
    assert await resp.content.read() == b"backup data"


async def test_error_on_agents_download(
    menuai_client: ClientSessionGenerator,
    webdav_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test we get not found on a not existing backup on download."""
    client = await menuai_client()
    backup_id = BACKUP_METADATA["backup_id"]
    webdav_client.list_files.return_value = []

    resp = await client.get(
        f"/api/backup/download/{backup_id}?agent_id={DOMAIN}.{mock_config_entry.entry_id}"
    )
    assert resp.status == 404


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (
            WebDavError("Unknown path"),
            "Backup operation failed: Unknown path",
        ),
        (TimeoutError(), "Backup operation timed out"),
    ],
)
async def test_delete_error(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    webdav_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    side_effect: Exception,
    error: str,
) -> None:
    """Test error during delete."""
    webdav_client.clean.side_effect = side_effect

    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {
            "type": "backup/delete",
            "backup_id": BACKUP_METADATA["backup_id"],
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agent_errors": {f"{DOMAIN}.{mock_config_entry.entry_id}": error}
    }


async def test_agents_delete_not_found_does_not_throw(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    webdav_client: AsyncMock,
) -> None:
    """Test agent delete backup."""
    webdav_client.list_files.return_value = {}
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {
            "type": "backup/delete",
            "backup_id": BACKUP_METADATA["backup_id"],
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"agent_errors": {}}


async def test_agents_backup_not_found(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    webdav_client: AsyncMock,
) -> None:
    """Test backup not found."""
    webdav_client.list_files.return_value = []
    backup_id = BACKUP_METADATA["backup_id"]
    client = await menuai_ws_client(menuai)
    await client.send_json_auto_id({"type": "backup/details", "backup_id": backup_id})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"]["backup"] is None


async def test_raises_on_403(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    webdav_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test we raise on 403."""
    webdav_client.list_files.side_effect = UnauthorizedError(
        "https://webdav.example.com"
    )
    backup_id = BACKUP_METADATA["backup_id"]
    client = await menuai_ws_client(menuai)
    await client.send_json_auto_id({"type": "backup/details", "backup_id": backup_id})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"]["agent_errors"] == {
        f"{DOMAIN}.{mock_config_entry.entry_id}": "Authentication error"
    }


async def test_listeners_get_cleaned_up(menuai: menuai) -> None:
    """Test listener gets cleaned up."""
    listener = AsyncMock()
    remove_listener = async_register_backup_agents_listener(menuai, listener=listener)

    # make sure it's the last listener
    menuai.data[DATA_BACKUP_AGENT_LISTENERS] = [listener]
    remove_listener()

    assert menuai.data.get(DATA_BACKUP_AGENT_LISTENERS) is None
