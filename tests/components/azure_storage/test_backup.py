"""Test the backups for OneDrive."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from io import StringIO
from unittest.mock import ANY, Mock, patch

from azure.core.exceptions import AzureError, HttpResponseError, ServiceRequestError
from azure.storage.blob import BlobProperties
import pytest

from menuai.components.azure_storage.backup import (
    async_register_backup_agents_listener,
)
from menuai.components.azure_storage.const import (
    DATA_BACKUP_AGENT_LISTENERS,
    DOMAIN,
)
from menuai.components.backup import DOMAIN as BACKUP_DOMAIN
from menuai.core import menuai
from menuai.helpers.backup import async_initialize_backup
from menuai.setup import async_setup_component

from . import setup_integration
from .const import BACKUP_METADATA, TEST_BACKUP

from tests.common import MockConfigEntry
from tests.typing import ClientSessionGenerator, MagicMock, WebSocketGenerator


@pytest.fixture(autouse=True)
async def setup_backup_integration(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up onedrive integration."""
    with (
        patch("menuai.components.backup.is_menuaiio", return_value=False),
        patch("menuai.components.backup.store.STORE_DELAY_SAVE", 0),
    ):
        async_initialize_backup(menuai)
        assert await async_setup_component(menuai, BACKUP_DOMAIN, {})
        await setup_integration(menuai, mock_config_entry)

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
                f"{DOMAIN}.{mock_config_entry.entry_id}": {
                    "protected": False,
                    "size": 34519040,
                }
            },
            "backup_id": "23e64aec",
            "database_included": True,
            "date": "2024-11-22T11:48:48.727189+01:00",
            "extra_metadata": {},
            "failed_addons": [],
            "failed_agent_ids": [],
            "failed_folders": [],
            "folders": [],
            "menuai_included": True,
            "menuai_version": "2024.12.0.dev0",
            "name": "Core 2024.12.0.dev0",
            "with_automatic_settings": None,
        }
    ]


async def test_agents_get_backup(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test agent get backup."""

    backup_id = TEST_BACKUP.backup_id
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
        "date": "2024-11-22T11:48:48.727189+01:00",
        "extra_metadata": {},
        "failed_addons": [],
        "failed_agent_ids": [],
        "failed_folders": [],
        "folders": [],
        "menuai_included": True,
        "menuai_version": "2024.12.0.dev0",
        "name": "Core 2024.12.0.dev0",
        "with_automatic_settings": None,
    }


async def test_agents_get_backup_does_not_throw_on_not_found(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test agent get backup does not throw on a backup not found."""

    client = await menuai_ws_client(menuai)
    await client.send_json_auto_id({"type": "backup/details", "backup_id": "random"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"]["agent_errors"] == {}
    assert response["result"]["backup"] is None


async def test_agents_delete(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    mock_client: MagicMock,
) -> None:
    """Test agent delete backup."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {
            "type": "backup/delete",
            "backup_id": TEST_BACKUP.backup_id,
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"agent_errors": {}}
    mock_client.delete_blob.assert_called_once()


async def test_agents_delete_not_throwing_on_not_found(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    mock_client: MagicMock,
) -> None:
    """Test agent delete backup does not throw on a backup not found."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {
            "type": "backup/delete",
            "backup_id": "random",
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"agent_errors": {}}
    assert mock_client.delete_blob.call_count == 0


async def test_agents_upload(
    menuai_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test agent upload backup."""
    client = await menuai_client()
    with (
        patch(
            "menuai.components.backup.manager.BackupManager.async_get_backup",
        ) as fetch_backup,
        patch(
            "menuai.components.backup.manager.read_backup",
            return_value=TEST_BACKUP,
        ),
        patch("pathlib.Path.open") as mocked_open,
    ):
        mocked_open.return_value.read = Mock(side_effect=[b"test", b""])
        fetch_backup.return_value = TEST_BACKUP
        resp = await client.post(
            f"/api/backup/upload?agent_id={DOMAIN}.{mock_config_entry.entry_id}",
            data={"file": StringIO("test")},
        )

    assert resp.status == 201
    assert f"Uploading backup {TEST_BACKUP.backup_id}" in caplog.text
    mock_client.upload_blob.assert_called_once_with(
        name="Core_2024.12.0.dev0_2024-11-22_11.48_48727189.tar",
        metadata=BACKUP_METADATA,
        data=ANY,
        length=ANY,
    )


async def test_agents_download(
    menuai_client: ClientSessionGenerator,
    mock_client: MagicMock,
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
    mock_client.download_blob.assert_called_once()


async def test_agents_error_on_download_not_found(
    menuai_client: ClientSessionGenerator,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test agent download backup."""

    async def async_list_blobs(
        metadata: dict[str, str],
    ) -> AsyncGenerator[BlobProperties]:
        yield BlobProperties(metadata=metadata)

    mock_client.list_blobs.side_effect = [
        async_list_blobs(BACKUP_METADATA),
        async_list_blobs({}),
    ]
    client = await menuai_client()
    backup_id = BACKUP_METADATA["backup_id"]

    resp = await client.get(
        f"/api/backup/download/{backup_id}?agent_id={DOMAIN}.{mock_config_entry.entry_id}"
    )
    assert resp.status == 404
    assert mock_client.download_blob.call_count == 0


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            HttpResponseError("http error"),
            "Error during backup operation in async_delete_backup: Status None, message: http error",
        ),
        (
            ServiceRequestError("timeout"),
            "Timeout during backup operation in async_delete_backup",
        ),
        (
            AzureError("generic error"),
            "Error during backup operation in async_delete_backup: generic error",
        ),
    ],
)
async def test_error_during_delete(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    error: Exception,
    message: str,
) -> None:
    """Test the error wrapper."""
    mock_client.delete_blob.side_effect = error

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
        "agent_errors": {f"{DOMAIN}.{mock_config_entry.entry_id}": message}
    }


async def test_listeners_get_cleaned_up(menuai: menuai) -> None:
    """Test listener gets cleaned up."""
    listener = MagicMock()
    remove_listener = async_register_backup_agents_listener(menuai, listener=listener)

    menuai.data[DATA_BACKUP_AGENT_LISTENERS] = [
        listener
    ]  # make sure it's the last listener
    remove_listener()

    assert menuai.data.get(DATA_BACKUP_AGENT_LISTENERS) is None
