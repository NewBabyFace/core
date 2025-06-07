"""Test the onboarding views."""

from io import StringIO
from typing import Any
from unittest.mock import ANY, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components import backup, onboarding
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers.backup import async_initialize_backup
from menuai.setup import async_setup_component

from tests.common import register_auth_provider
from tests.typing import ClientSessionGenerator


def mock_onboarding_storage(menuai_storage, data):
    """Mock the onboarding storage."""
    menuai_storage[onboarding.STORAGE_KEY] = {
        "version": onboarding.STORAGE_VERSION,
        "data": data,
    }


@pytest.fixture(autouse=True)
def auth_active(menuai: menuai) -> None:
    """Ensure auth is always active."""
    menuai.loop.run_until_complete(
        register_auth_provider(menuai, {"type": "menuai"})
    )


@pytest.mark.parametrize(
    ("method", "view", "kwargs"),
    [
        ("get", "backup/info", {}),
        (
            "post",
            "backup/restore",
            {"json": {"backup_id": "abc123", "agent_id": "test"}},
        ),
        ("post", "backup/upload", {}),
    ],
)
async def test_onboarding_view_after_done(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    menuai_client: ClientSessionGenerator,
    method: str,
    view: str,
    kwargs: dict[str, Any],
) -> None:
    """Test raising after onboarding."""
    mock_onboarding_storage(menuai_storage, {"done": [onboarding.const.STEP_USER]})

    assert await async_setup_component(menuai, "onboarding", {})
    async_initialize_backup(menuai)
    assert await async_setup_component(menuai, "backup", {})
    await menuai.async_block_till_done()

    client = await menuai_client()

    resp = await client.request(method, f"/api/onboarding/{view}", **kwargs)

    assert resp.status == 401


@pytest.mark.parametrize(
    ("method", "view", "kwargs"),
    [
        ("get", "backup/info", {}),
        (
            "post",
            "backup/restore",
            {"json": {"backup_id": "abc123", "agent_id": "test"}},
        ),
        ("post", "backup/upload", {}),
    ],
)
async def test_onboarding_backup_view_without_backup(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    menuai_client: ClientSessionGenerator,
    method: str,
    view: str,
    kwargs: dict[str, Any],
) -> None:
    """Test interacting with backup wievs when backup integration is missing."""
    mock_onboarding_storage(menuai_storage, {"done": []})

    assert await async_setup_component(menuai, "onboarding", {})
    await menuai.async_block_till_done()

    client = await menuai_client()

    resp = await client.request(method, f"/api/onboarding/{view}", **kwargs)

    assert resp.status == 404


async def test_onboarding_backup_info(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test backup info."""
    mock_onboarding_storage(menuai_storage, {"done": []})

    assert await async_setup_component(menuai, "onboarding", {})
    async_initialize_backup(menuai)
    assert await async_setup_component(menuai, "backup", {})
    await menuai.async_block_till_done()

    client = await menuai_client()

    backups = {
        "abc123": backup.ManagerBackup(
            addons=[backup.AddonInfo(name="Test", slug="test", version="1.0.0")],
            agents={
                "backup.local": backup.manager.AgentBackupStatus(protected=True, size=0)
            },
            backup_id="abc123",
            database_included=True,
            date="1970-01-01T00:00:00.000Z",
            extra_metadata={"instance_id": "abc123", "with_automatic_settings": True},
            failed_addons=[],
            failed_agent_ids=[],
            failed_folders=[],
            folders=[backup.Folder.MEDIA, backup.Folder.SHARE],
            menuai_included=True,
            menuai_version="2024.12.0",
            name="Test",
            with_automatic_settings=True,
        ),
        "def456": backup.ManagerBackup(
            addons=[],
            agents={
                "test.remote": backup.manager.AgentBackupStatus(protected=True, size=0)
            },
            backup_id="def456",
            database_included=False,
            date="1980-01-01T00:00:00.000Z",
            extra_metadata={
                "instance_id": "unknown_uuid",
                "with_automatic_settings": True,
            },
            failed_addons=[],
            failed_agent_ids=[],
            failed_folders=[],
            folders=[backup.Folder.MEDIA, backup.Folder.SHARE],
            menuai_included=True,
            menuai_version="2024.12.0",
            name="Test 2",
            with_automatic_settings=None,
        ),
    }

    with patch(
        "menuai.components.backup.manager.BackupManager.async_get_backups",
        return_value=(backups, {}),
    ):
        resp = await client.get("/api/onboarding/backup/info")

        assert resp.status == 200
        assert await resp.json() == snapshot


@pytest.mark.parametrize(
    ("params", "expected_kwargs"),
    [
        (
            {"backup_id": "abc123", "agent_id": "backup.local"},
            {
                "agent_id": "backup.local",
                "password": None,
                "restore_addons": None,
                "restore_database": True,
                "restore_folders": None,
                "restore_menuai": True,
            },
        ),
        (
            {
                "backup_id": "abc123",
                "agent_id": "backup.local",
                "password": "hunter2",
                "restore_addons": ["addon_1"],
                "restore_database": True,
                "restore_folders": ["media"],
            },
            {
                "agent_id": "backup.local",
                "password": "hunter2",
                "restore_addons": ["addon_1"],
                "restore_database": True,
                "restore_folders": [backup.Folder.MEDIA],
                "restore_menuai": True,
            },
        ),
        (
            {
                "backup_id": "abc123",
                "agent_id": "backup.local",
                "password": "hunter2",
                "restore_addons": ["addon_1", "addon_2"],
                "restore_database": False,
                "restore_folders": ["media", "share"],
            },
            {
                "agent_id": "backup.local",
                "password": "hunter2",
                "restore_addons": ["addon_1", "addon_2"],
                "restore_database": False,
                "restore_folders": [backup.Folder.MEDIA, backup.Folder.SHARE],
                "restore_menuai": True,
            },
        ),
    ],
)
async def test_onboarding_backup_restore(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    menuai_client: ClientSessionGenerator,
    params: dict[str, Any],
    expected_kwargs: dict[str, Any],
) -> None:
    """Test restore backup."""
    mock_onboarding_storage(menuai_storage, {"done": []})

    assert await async_setup_component(menuai, "onboarding", {})
    async_initialize_backup(menuai)
    assert await async_setup_component(menuai, "backup", {})
    await menuai.async_block_till_done()

    client = await menuai_client()

    with patch(
        "menuai.components.backup.manager.BackupManager.async_restore_backup",
    ) as mock_restore:
        resp = await client.post("/api/onboarding/backup/restore", json=params)
    assert resp.status == 200
    mock_restore.assert_called_once_with("abc123", **expected_kwargs)


@pytest.mark.parametrize(
    ("params", "restore_error", "expected_status", "expected_json", "restore_calls"),
    [
        # Missing agent_id
        (
            {"backup_id": "abc123"},
            None,
            400,
            {
                "message": "Message format incorrect: required key not provided @ data['agent_id']"
            },
            0,
        ),
        # Missing backup_id
        (
            {"agent_id": "backup.local"},
            None,
            400,
            {
                "message": "Message format incorrect: required key not provided @ data['backup_id']"
            },
            0,
        ),
        # Invalid restore_database
        (
            {
                "backup_id": "abc123",
                "agent_id": "backup.local",
                "restore_database": "yes_please",
            },
            None,
            400,
            {
                "message": "Message format incorrect: expected bool for dictionary value @ data['restore_database']"
            },
            0,
        ),
        # Invalid folder
        (
            {
                "backup_id": "abc123",
                "agent_id": "backup.local",
                "restore_folders": ["invalid"],
            },
            None,
            400,
            {
                "message": "Message format incorrect: expected Folder or one of 'share', 'addons/local', 'ssl', 'media' @ data['restore_folders'][0]"
            },
            0,
        ),
        # Wrong password
        (
            {"backup_id": "abc123", "agent_id": "backup.local"},
            backup.IncorrectPasswordError,
            400,
            {"code": "incorrect_password"},
            1,
        ),
        # MenuAI error
        (
            {"backup_id": "abc123", "agent_id": "backup.local"},
            menuaiError("Boom!"),
            400,
            {"code": "restore_failed", "message": "Boom!"},
            1,
        ),
    ],
)
async def test_onboarding_backup_restore_error(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    menuai_client: ClientSessionGenerator,
    params: dict[str, Any],
    restore_error: Exception | None,
    expected_status: int,
    expected_json: str,
    restore_calls: int,
) -> None:
    """Test restore backup fails."""
    mock_onboarding_storage(menuai_storage, {"done": []})

    assert await async_setup_component(menuai, "onboarding", {})
    async_initialize_backup(menuai)
    assert await async_setup_component(menuai, "backup", {})
    await menuai.async_block_till_done()

    client = await menuai_client()

    with patch(
        "menuai.components.backup.manager.BackupManager.async_restore_backup",
        side_effect=restore_error,
    ) as mock_restore:
        resp = await client.post("/api/onboarding/backup/restore", json=params)

    assert resp.status == expected_status
    assert await resp.json() == expected_json
    assert len(mock_restore.mock_calls) == restore_calls


@pytest.mark.parametrize(
    ("params", "restore_error", "expected_status", "expected_message", "restore_calls"),
    [
        # Unexpected error
        (
            {"backup_id": "abc123", "agent_id": "backup.local"},
            Exception("Boom!"),
            500,
            "500 Internal Server Error",
            1,
        ),
    ],
)
async def test_onboarding_backup_restore_unexpected_error(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    menuai_client: ClientSessionGenerator,
    params: dict[str, Any],
    restore_error: Exception | None,
    expected_status: int,
    expected_message: str,
    restore_calls: int,
) -> None:
    """Test restore backup fails."""
    mock_onboarding_storage(menuai_storage, {"done": []})

    assert await async_setup_component(menuai, "onboarding", {})
    async_initialize_backup(menuai)
    assert await async_setup_component(menuai, "backup", {})
    await menuai.async_block_till_done()

    client = await menuai_client()

    with patch(
        "menuai.components.backup.manager.BackupManager.async_restore_backup",
        side_effect=restore_error,
    ) as mock_restore:
        resp = await client.post("/api/onboarding/backup/restore", json=params)

    assert resp.status == expected_status
    assert (await resp.content.read()).decode().startswith(expected_message)
    assert len(mock_restore.mock_calls) == restore_calls


async def test_onboarding_backup_upload(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test upload backup."""
    mock_onboarding_storage(menuai_storage, {"done": []})

    assert await async_setup_component(menuai, "onboarding", {})
    async_initialize_backup(menuai)
    assert await async_setup_component(menuai, "backup", {})
    await menuai.async_block_till_done()

    client = await menuai_client()

    with patch(
        "menuai.components.backup.manager.BackupManager.async_receive_backup",
        return_value="abc123",
    ) as mock_receive:
        resp = await client.post(
            "/api/onboarding/backup/upload?agent_id=backup.local",
            data={"file": StringIO("test")},
        )
    assert resp.status == 201
    assert await resp.json() == {"backup_id": "abc123"}
    mock_receive.assert_called_once_with(agent_ids=["backup.local"], contents=ANY)
