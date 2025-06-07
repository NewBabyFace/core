"""Test the Kitchen Sink backup platform."""

from collections.abc import AsyncGenerator
from io import StringIO
from unittest.mock import ANY, patch

import pytest

from menuai.components.backup import (
    DOMAIN as BACKUP_DOMAIN,
    AddonInfo,
    AgentBackup,
    Folder,
)
from menuai.components.kitchen_sink import DOMAIN
from menuai.core import menuai
from menuai.helpers import instance_id
from menuai.helpers.backup import async_initialize_backup
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator, WebSocketGenerator


@pytest.fixture(autouse=True)
async def backup_only() -> AsyncGenerator[None]:
    """Enable only the backup platform.

    The backup platform is not an entity platform.
    """
    with patch(
        "menuai.components.kitchen_sink.COMPONENTS_WITH_DEMO_PLATFORM",
        [],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_integration(menuai: menuai) -> AsyncGenerator[None]:
    """Set up Kitchen Sink and backup integrations."""
    async_initialize_backup(menuai)
    with patch("menuai.components.backup.is_menuaiio", return_value=False):
        assert await async_setup_component(menuai, BACKUP_DOMAIN, {BACKUP_DOMAIN: {}})
        assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()
        yield


async def test_agents_info(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test backup agent info."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agents": [
            {"agent_id": "backup.local", "name": "local"},
            {"agent_id": "kitchen_sink.syncer", "name": "syncer"},
        ],
    }

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()

    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agents": [{"agent_id": "backup.local", "name": "local"}]
    }

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agents": [
            {"agent_id": "backup.local", "name": "local"},
            {"agent_id": "kitchen_sink.syncer", "name": "syncer"},
        ],
    }


async def test_agents_list_backups(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test agent list backups."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id({"type": "backup/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"]["backups"] == [
        {
            "addons": [{"name": "Test", "slug": "test", "version": "1.0.0"}],
            "agents": {"kitchen_sink.syncer": {"protected": False, "size": 1234}},
            "backup_id": "abc123",
            "database_included": False,
            "date": "1970-01-01T00:00:00Z",
            "extra_metadata": {},
            "failed_addons": [],
            "failed_agent_ids": [],
            "failed_folders": [],
            "folders": ["media", "share"],
            "menuai_included": True,
            "menuai_version": "2024.12.0",
            "name": "Kitchen sink syncer",
            "with_automatic_settings": None,
        }
    ]


async def test_agents_download(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test downloading a backup."""
    client = await menuai_client()

    resp = await client.get("/api/backup/download/abc123?agent_id=kitchen_sink.syncer")
    assert resp.status == 200
    assert await resp.content.read() == b"backup data"


async def test_agents_upload(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_ws_client: WebSocketGenerator,
    caplog: pytest.LogCaptureFixture,
    menuai_supervisor_access_token: str,
) -> None:
    """Test agent upload backup."""
    ws_client = await menuai_ws_client(menuai, menuai_supervisor_access_token)
    client = await menuai_client()
    backup_id = "test-backup"
    test_backup = AgentBackup(
        addons=[AddonInfo(name="Test", slug="test", version="1.0.0")],
        backup_id=backup_id,
        database_included=True,
        date="1970-01-01T00:00:00.000Z",
        extra_metadata={
            "instance_id": await instance_id.async_get(menuai),
            "with_automatic_settings": False,
        },
        folders=[Folder.MEDIA, Folder.SHARE],
        menuai_included=True,
        menuai_version="2024.12.0",
        name="Test",
        protected=False,
        size=0.0,
    )

    with (
        patch("pathlib.Path.open"),
        patch(
            "menuai.components.backup.manager.BackupManager.async_get_backup",
        ) as fetch_backup,
        patch(
            "menuai.components.backup.manager.read_backup",
            return_value=test_backup,
        ),
    ):
        fetch_backup.return_value = test_backup
        resp = await client.post(
            "/api/backup/upload?agent_id=kitchen_sink.syncer",
            data={"file": StringIO("test")},
        )

    assert resp.status == 201
    assert f"Uploading backup {backup_id}" in caplog.text

    await ws_client.send_json_auto_id({"type": "backup/info"})
    response = await ws_client.receive_json()

    assert response["success"]
    backup_list = response["result"]["backups"]
    assert len(backup_list) == 2
    assert backup_list[1] == {
        "addons": [{"name": "Test", "slug": "test", "version": "1.0.0"}],
        "agents": {"kitchen_sink.syncer": {"protected": False, "size": 0.0}},
        "backup_id": "test-backup",
        "database_included": True,
        "date": "1970-01-01T00:00:00.000Z",
        "extra_metadata": {"instance_id": ANY, "with_automatic_settings": False},
        "failed_addons": [],
        "failed_agent_ids": [],
        "failed_folders": [],
        "folders": ["media", "share"],
        "menuai_included": True,
        "menuai_version": "2024.12.0",
        "name": "Test",
        "with_automatic_settings": False,
    }


async def test_agent_delete_backup(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test agent delete backup."""
    client = await menuai_ws_client(menuai)
    backup_id = "abc123"

    await client.send_json_auto_id(
        {
            "type": "backup/delete",
            "backup_id": backup_id,
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert f"Deleted backup {backup_id}" in caplog.text

    await client.send_json_auto_id({"type": "backup/info"})
    response = await client.receive_json()

    assert response["success"]
    backup_list = response["result"]["backups"]
    assert not backup_list
