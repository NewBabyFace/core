"""Test websocket API."""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from aiohasupervisor import SupervisorError
from aiohasupervisor.models import menuaiUpdateOptions, StoreAddonUpdate
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.backup import BackupManagerError, ManagerBackup

# pylint: disable-next=menuai-component-root-import
from menuai.components.backup.manager import AgentBackupStatus
from menuai.components.menuaiio import DOMAIN
from menuai.components.menuaiio.const import (
    ATTR_DATA,
    ATTR_ENDPOINT,
    ATTR_METHOD,
    ATTR_WS_EVENT,
    EVENT_SUPERVISOR_EVENT,
    WS_ID,
    WS_TYPE,
    WS_TYPE_API,
    WS_TYPE_SUBSCRIBE,
)
from menuai.const import __version__ as HAVERSION
from menuai.core import menuai
from menuai.helpers.backup import async_initialize_backup
from menuai.helpers.dispatcher import async_dispatcher_send
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, MockUser, async_mock_signal
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import WebSocketGenerator

MOCK_ENVIRON = {"SUPERVISOR": "127.0.0.1", "SUPERVISOR_TOKEN": "abcdefgh"}


@pytest.fixture(autouse=True)
def mock_all(
    aioclient_mock: AiohttpClientMocker,
    supervisor_is_connected: AsyncMock,
    resolution_info: AsyncMock,
    addon_info: AsyncMock,
) -> None:
    """Mock all setup requests."""
    aioclient_mock.post("http://127.0.0.1/menuai/options", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/supervisor/options", json={"result": "ok"})
    aioclient_mock.get(
        "http://127.0.0.1/info",
        json={
            "result": "ok",
            "data": {"supervisor": "222", "menuai": "0.110.0", "menuaios": None},
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/host/info",
        json={
            "result": "ok",
            "data": {
                "result": "ok",
                "data": {
                    "cmenuaiis": "vm",
                    "operating_system": "Debian GNU/Linux 10 (buster)",
                    "kernel": "4.19.0-6-amd64",
                },
            },
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/core/info",
        json={"result": "ok", "data": {"version_latest": "1.0.0", "version": "1.0.0"}},
    )
    aioclient_mock.get(
        "http://127.0.0.1/os/info",
        json={"result": "ok", "data": {"version_latest": "1.0.0"}},
    )
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/info",
        json={
            "result": "ok",
            "data": {
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "auto_update": True,
                "addons": [
                    {
                        "name": "test",
                        "state": "started",
                        "slug": "test",
                        "installed": True,
                        "update_available": True,
                        "icon": False,
                        "version": "2.0.0",
                        "version_latest": "2.0.1",
                        "repository": "core",
                        "url": "https://github.com/home-assistant/addons/test",
                    },
                ],
            },
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/ingress/panels", json={"result": "ok", "data": {"panels": {}}}
    )
    aioclient_mock.get(
        "http://127.0.0.1/network/info",
        json={
            "result": "ok",
            "data": {
                "host_internet": True,
                "supervisor_internet": True,
            },
        },
    )


@pytest.mark.usefixtures("menuaiio_env")
async def test_ws_subscription(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test websocket subscription."""
    assert await async_setup_component(menuai, "menuaiio", {})
    client = await menuai_ws_client(menuai)
    await client.send_json({WS_ID: 5, WS_TYPE: WS_TYPE_SUBSCRIBE})
    response = await client.receive_json()
    assert response["success"]

    calls = async_mock_signal(menuai, EVENT_SUPERVISOR_EVENT)
    async_dispatcher_send(menuai, EVENT_SUPERVISOR_EVENT, {"lorem": "ipsum"})

    response = await client.receive_json()
    assert response["event"]["lorem"] == "ipsum"
    assert len(calls) == 1

    await client.send_json(
        {
            WS_ID: 6,
            WS_TYPE: "supervisor/event",
            ATTR_DATA: {ATTR_WS_EVENT: "test", "lorem": "ipsum"},
        }
    )
    response = await client.receive_json()
    assert response["success"]
    assert len(calls) == 2

    response = await client.receive_json()
    assert response["event"]["lorem"] == "ipsum"

    # Unsubscribe
    await client.send_json({WS_ID: 7, WS_TYPE: "unsubscribe_events", "subscription": 5})
    response = await client.receive_json()
    assert response["success"]


@pytest.mark.usefixtures("menuaiio_env")
async def test_websocket_supervisor_api(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test Supervisor websocket api."""
    assert await async_setup_component(menuai, "menuaiio", {})
    websocket_client = await menuai_ws_client(menuai)
    aioclient_mock.post(
        "http://127.0.0.1/backups/new/partial",
        json={"result": "ok", "data": {"slug": "sn_slug"}},
    )

    await websocket_client.send_json(
        {
            WS_ID: 1,
            WS_TYPE: WS_TYPE_API,
            ATTR_ENDPOINT: "/backups/new/partial",
            ATTR_METHOD: "post",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["result"]["slug"] == "sn_slug"

    await websocket_client.send_json(
        {
            WS_ID: 2,
            WS_TYPE: WS_TYPE_API,
            ATTR_ENDPOINT: "/supervisor/info",
            ATTR_METHOD: "get",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["result"]["version_latest"] == "1.0.0"

    assert aioclient_mock.mock_calls[-1][3] == {
        "X-menuai-Source": "core.websocket_api",
        "Authorization": "Bearer 123456",
    }


@pytest.mark.usefixtures("menuaiio_env")
async def test_websocket_supervisor_api_error(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test Supervisor websocket api error."""
    assert await async_setup_component(menuai, "menuaiio", {})
    websocket_client = await menuai_ws_client(menuai)
    aioclient_mock.get(
        "http://127.0.0.1/ping",
        json={"result": "error", "message": "example error"},
        status=400,
    )

    await websocket_client.send_json(
        {
            WS_ID: 1,
            WS_TYPE: WS_TYPE_API,
            ATTR_ENDPOINT: "/ping",
            ATTR_METHOD: "get",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["error"]["code"] == "unknown_error"
    assert msg["error"]["message"] == "example error"


@pytest.mark.usefixtures("menuaiio_env")
async def test_websocket_supervisor_api_error_without_msg(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test Supervisor websocket api error."""
    assert await async_setup_component(menuai, "menuaiio", {})
    websocket_client = await menuai_ws_client(menuai)
    aioclient_mock.get(
        "http://127.0.0.1/ping",
        json={},
        status=400,
    )

    await websocket_client.send_json(
        {
            WS_ID: 1,
            WS_TYPE: WS_TYPE_API,
            ATTR_ENDPOINT: "/ping",
            ATTR_METHOD: "get",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["error"]["code"] == "unknown_error"
    assert msg["error"]["message"] == ""


@pytest.mark.usefixtures("menuaiio_env")
async def test_websocket_non_admin_user(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    aioclient_mock: AiohttpClientMocker,
    menuai_admin_user: MockUser,
) -> None:
    """Test Supervisor websocket api error."""
    menuai_admin_user.groups = []
    assert await async_setup_component(menuai, "menuaiio", {})
    websocket_client = await menuai_ws_client(menuai)
    aioclient_mock.get(
        "http://127.0.0.1/addons/test_addon/info",
        json={"result": "ok", "data": {}},
    )
    aioclient_mock.get(
        "http://127.0.0.1/ingress/session",
        json={"result": "ok", "data": {}},
    )
    aioclient_mock.get(
        "http://127.0.0.1/ingress/validate_session",
        json={"result": "ok", "data": {}},
    )

    await websocket_client.send_json(
        {
            WS_ID: 1,
            WS_TYPE: WS_TYPE_API,
            ATTR_ENDPOINT: "/addons/test_addon/info",
            ATTR_METHOD: "get",
        }
    )
    msg = await websocket_client.receive_json()
    assert msg["result"] == {}

    await websocket_client.send_json(
        {
            WS_ID: 2,
            WS_TYPE: WS_TYPE_API,
            ATTR_ENDPOINT: "/ingress/session",
            ATTR_METHOD: "get",
        }
    )
    msg = await websocket_client.receive_json()
    assert msg["result"] == {}

    await websocket_client.send_json(
        {
            WS_ID: 3,
            WS_TYPE: WS_TYPE_API,
            ATTR_ENDPOINT: "/ingress/validate_session",
            ATTR_METHOD: "get",
        }
    )
    msg = await websocket_client.receive_json()
    assert msg["result"] == {}

    await websocket_client.send_json(
        {
            WS_ID: 4,
            WS_TYPE: WS_TYPE_API,
            ATTR_ENDPOINT: "/supervisor/info",
            ATTR_METHOD: "get",
        }
    )

    msg = await websocket_client.receive_json()
    assert msg["error"]["message"] == "Unauthorized"


async def test_update_addon(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    update_addon: AsyncMock,
) -> None:
    """Test updating addon."""
    client = await menuai_ws_client(menuai)
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
        assert result
    await menuai.async_block_till_done()

    with patch(
        "menuai.components.backup.manager.BackupManager.async_create_backup",
    ) as mock_create_backup:
        await client.send_json_auto_id(
            {"type": "menuaiio/update/addon", "addon": "test", "backup": False}
        )
        result = await client.receive_json()
        assert result["success"]
    mock_create_backup.assert_not_called()
    update_addon.assert_called_once_with("test", StoreAddonUpdate(backup=False))


async def setup_backup_integration(menuai: menuai) -> None:
    """Set up the backup integration."""
    async_initialize_backup(menuai)
    assert await async_setup_component(menuai, "backup", {})
    await menuai.async_block_till_done()


@pytest.mark.parametrize(
    ("commands", "default_mount", "expected_kwargs"),
    [
        (
            [],
            None,
            {
                "agent_ids": ["menuaiio.local"],
                "extra_metadata": {"supervisor.addon_update": "test"},
                "include_addons": ["test"],
                "include_all_addons": False,
                "include_database": False,
                "include_folders": None,
                "include_menuai": False,
                "name": "test 2.0.0",
                "password": None,
            },
        ),
        (
            [],
            "my_nas",
            {
                "agent_ids": ["menuaiio.my_nas"],
                "extra_metadata": {"supervisor.addon_update": "test"},
                "include_addons": ["test"],
                "include_all_addons": False,
                "include_database": False,
                "include_folders": None,
                "include_menuai": False,
                "name": "test 2.0.0",
                "password": None,
            },
        ),
        (
            [
                {
                    "type": "backup/config/update",
                    "create_backup": {
                        "agent_ids": ["test-agent"],
                        "include_addons": ["my-addon"],
                        "include_all_addons": True,
                        "include_database": False,
                        "include_folders": ["share"],
                        "name": "cool_backup",
                        "password": "hunter2",
                    },
                },
            ],
            None,
            {
                "agent_ids": ["menuaiio.local"],
                "extra_metadata": {"supervisor.addon_update": "test"},
                "include_addons": ["test"],
                "include_all_addons": False,
                "include_database": False,
                "include_folders": None,
                "include_menuai": False,
                "name": "test 2.0.0",
                "password": "hunter2",
            },
        ),
    ],
)
async def test_update_addon_with_backup(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    supervisor_client: AsyncMock,
    update_addon: AsyncMock,
    commands: list[dict[str, Any]],
    default_mount: str | None,
    expected_kwargs: dict[str, Any],
) -> None:
    """Test updating addon with backup."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
        assert result
    await setup_backup_integration(menuai)

    client = await menuai_ws_client(menuai)
    for command in commands:
        await client.send_json_auto_id(command)
        result = await client.receive_json()
        assert result["success"]

    supervisor_client.mounts.info.return_value.default_backup_mount = default_mount
    with patch(
        "menuai.components.backup.manager.BackupManager.async_create_backup",
    ) as mock_create_backup:
        await client.send_json_auto_id(
            {"type": "menuaiio/update/addon", "addon": "test", "backup": True}
        )
        result = await client.receive_json()
        assert result["success"]
    mock_create_backup.assert_called_once_with(**expected_kwargs)
    update_addon.assert_called_once_with("test", StoreAddonUpdate(backup=False))


@pytest.mark.parametrize(
    ("ws_commands", "backups", "removed_backups"),
    [
        (
            [],
            {},
            [],
        ),
        (
            [],
            {
                "backup-1": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-10T04:45:00+01:00",
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
                "backup-2": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-11T04:45:00+01:00",
                    with_automatic_settings=False,
                    spec=ManagerBackup,
                ),
                "backup-3": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-11T04:45:00+01:00",
                    extra_metadata={"supervisor.addon_update": "other"},
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
                "backup-4": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-11T04:45:00+01:00",
                    extra_metadata={"supervisor.addon_update": "other"},
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
                "backup-5": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-11T04:45:00+01:00",
                    extra_metadata={"supervisor.addon_update": "test"},
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
                "backup-6": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-12T04:45:00+01:00",
                    extra_metadata={"supervisor.addon_update": "test"},
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
            },
            ["backup-5"],
        ),
        (
            [{"type": "menuaiio/update/config/update", "add_on_backup_retain_copies": 2}],
            {
                "backup-1": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-10T04:45:00+01:00",
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
                "backup-2": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-11T04:45:00+01:00",
                    with_automatic_settings=False,
                    spec=ManagerBackup,
                ),
                "backup-3": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-11T04:45:00+01:00",
                    extra_metadata={"supervisor.addon_update": "other"},
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
                "backup-4": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-11T04:45:00+01:00",
                    extra_metadata={"supervisor.addon_update": "other"},
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
                "backup-5": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-11T04:45:00+01:00",
                    extra_metadata={"supervisor.addon_update": "test"},
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
                "backup-6": MagicMock(
                    agents={"menuaiio.local": MagicMock(spec=AgentBackupStatus)},
                    date="2024-11-12T04:45:00+01:00",
                    extra_metadata={"supervisor.addon_update": "test"},
                    with_automatic_settings=True,
                    spec=ManagerBackup,
                ),
            },
            [],
        ),
    ],
)
async def test_update_addon_with_backup_removes_old_backups(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    supervisor_client: AsyncMock,
    update_addon: AsyncMock,
    ws_commands: list[dict[str, Any]],
    backups: dict[str, ManagerBackup],
    removed_backups: list[str],
) -> None:
    """Test updating addon update entity."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
        assert result
    await setup_backup_integration(menuai)

    client = await menuai_ws_client(menuai)

    for command in ws_commands:
        await client.send_json_auto_id(command)
        result = await client.receive_json()
        assert result["success"]

    supervisor_client.mounts.info.return_value.default_backup_mount = None
    with (
        patch(
            "menuai.components.backup.manager.BackupManager.async_create_backup",
        ) as mock_create_backup,
        patch(
            "menuai.components.backup.manager.BackupManager.async_delete_backup",
            autospec=True,
            return_value={},
        ) as async_delete_backup,
        patch(
            "menuai.components.backup.manager.BackupManager.async_get_backups",
            return_value=(backups, {}),
        ),
    ):
        await client.send_json_auto_id(
            {"type": "menuaiio/update/addon", "addon": "test", "backup": True}
        )
        result = await client.receive_json()
        assert result["success"]
    mock_create_backup.assert_called_once_with(
        agent_ids=["menuaiio.local"],
        extra_metadata={"supervisor.addon_update": "test"},
        include_addons=["test"],
        include_all_addons=False,
        include_database=False,
        include_folders=None,
        include_menuai=False,
        name="test 2.0.0",
        password=None,
    )
    assert len(async_delete_backup.mock_calls) == len(removed_backups)
    for call in async_delete_backup.mock_calls:
        assert call.args[1] in removed_backups
    update_addon.assert_called_once_with("test", StoreAddonUpdate(backup=False))


async def test_update_core(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    supervisor_client: AsyncMock,
) -> None:
    """Test updating core."""
    client = await menuai_ws_client(menuai)
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
        assert result
    await menuai.async_block_till_done()

    supervisor_client.menuai.update.return_value = None
    with patch(
        "menuai.components.backup.manager.BackupManager.async_create_backup",
    ) as mock_create_backup:
        await client.send_json_auto_id({"type": "menuaiio/update/core", "backup": False})
        result = await client.receive_json()
        assert result["success"]
    mock_create_backup.assert_not_called()
    supervisor_client.menuai.update.assert_called_once_with(
        menuaiUpdateOptions(version=None, backup=False)
    )


@pytest.mark.parametrize(
    ("commands", "default_mount", "expected_kwargs"),
    [
        (
            [],
            None,
            {
                "agent_ids": ["menuaiio.local"],
                "include_addons": None,
                "include_all_addons": False,
                "include_database": True,
                "include_folders": None,
                "include_menuai": True,
                "name": f"MenuAI Core {HAVERSION}",
                "password": None,
            },
        ),
        (
            [],
            "my_nas",
            {
                "agent_ids": ["menuaiio.my_nas"],
                "include_addons": None,
                "include_all_addons": False,
                "include_database": True,
                "include_folders": None,
                "include_menuai": True,
                "name": f"MenuAI Core {HAVERSION}",
                "password": None,
            },
        ),
        (
            [
                {
                    "type": "backup/config/update",
                    "create_backup": {
                        "agent_ids": ["test-agent"],
                        "include_addons": ["my-addon"],
                        "include_all_addons": True,
                        "include_database": False,
                        "include_folders": ["share"],
                        "name": "cool_backup",
                        "password": "hunter2",
                    },
                },
            ],
            None,
            {
                "agent_ids": ["test-agent"],
                "include_addons": ["my-addon"],
                "include_all_addons": True,
                "include_database": False,
                "include_folders": ["share"],
                "include_menuai": True,
                "name": "cool_backup",
                "password": "hunter2",
                "with_automatic_settings": True,
            },
        ),
    ],
)
async def test_update_core_with_backup(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    supervisor_client: AsyncMock,
    commands: list[dict[str, Any]],
    default_mount: str | None,
    expected_kwargs: dict[str, Any],
) -> None:
    """Test updating core with backup."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
        assert result
    await setup_backup_integration(menuai)

    client = await menuai_ws_client(menuai)
    for command in commands:
        await client.send_json_auto_id(command)
        result = await client.receive_json()
        assert result["success"]

    supervisor_client.menuai.update.return_value = None
    supervisor_client.mounts.info.return_value.default_backup_mount = default_mount
    with patch(
        "menuai.components.backup.manager.BackupManager.async_create_backup",
    ) as mock_create_backup:
        await client.send_json_auto_id({"type": "menuaiio/update/core", "backup": True})
        result = await client.receive_json()
        assert result["success"]
    mock_create_backup.assert_called_once_with(**expected_kwargs)
    supervisor_client.menuai.update.assert_called_once_with(
        menuaiUpdateOptions(version=None, backup=False)
    )


async def test_update_addon_with_error(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    update_addon: AsyncMock,
) -> None:
    """Test updating addon with error."""
    client = await menuai_ws_client(menuai)
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)

    with patch.dict(os.environ, MOCK_ENVIRON):
        assert await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
    await menuai.async_block_till_done()

    update_addon.side_effect = SupervisorError
    await client.send_json_auto_id(
        {"type": "menuaiio/update/addon", "addon": "test", "backup": False}
    )
    result = await client.receive_json()
    assert not result["success"]
    assert result["error"] == {
        "code": "home_assistant_error",
        "message": "Error updating test: ",
    }


@pytest.mark.parametrize(
    ("create_backup_error", "delete_filtered_backups_error", "message"),
    [
        (BackupManagerError, None, "Error creating backup: "),
        (None, BackupManagerError, "Error deleting old backups: "),
    ],
)
async def test_update_addon_with_backup_and_error(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    supervisor_client: AsyncMock,
    create_backup_error: Exception | None,
    delete_filtered_backups_error: Exception | None,
    message: str,
) -> None:
    """Test updating addon with backup and error."""
    client = await menuai_ws_client(menuai)
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
        assert result
    await setup_backup_integration(menuai)

    supervisor_client.menuai.update.return_value = None
    supervisor_client.mounts.info.return_value.default_backup_mount = None
    with (
        patch(
            "menuai.components.backup.manager.BackupManager.async_create_backup",
            side_effect=create_backup_error,
        ),
        patch(
            "menuai.components.backup.manager.BackupManager.async_delete_filtered_backups",
            side_effect=delete_filtered_backups_error,
        ),
    ):
        await client.send_json_auto_id(
            {"type": "menuaiio/update/addon", "addon": "test", "backup": True}
        )
        result = await client.receive_json()
    assert not result["success"]
    assert result["error"] == {"code": "home_assistant_error", "message": message}


async def test_update_core_with_error(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    supervisor_client: AsyncMock,
) -> None:
    """Test updating core with error."""
    client = await menuai_ws_client(menuai)
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)

    with patch.dict(os.environ, MOCK_ENVIRON):
        assert await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
    await menuai.async_block_till_done()

    supervisor_client.menuai.update.side_effect = SupervisorError
    await client.send_json_auto_id({"type": "menuaiio/update/core", "backup": False})
    result = await client.receive_json()
    assert not result["success"]
    assert result["error"] == {
        "code": "home_assistant_error",
        "message": "Error updating MenuAI Core: ",
    }


async def test_update_core_with_backup_and_error(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    supervisor_client: AsyncMock,
) -> None:
    """Test updating core with backup and error."""
    client = await menuai_ws_client(menuai)
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
        assert result
    await setup_backup_integration(menuai)

    supervisor_client.menuai.update.return_value = None
    supervisor_client.mounts.info.return_value.default_backup_mount = None
    with (
        patch(
            "menuai.components.backup.manager.BackupManager.async_create_backup",
            side_effect=BackupManagerError,
        ),
    ):
        await client.send_json_auto_id({"type": "menuaiio/update/core", "backup": True})
        result = await client.receive_json()
    assert not result["success"]
    assert result["error"] == {
        "code": "home_assistant_error",
        "message": "Error creating backup: ",
    }


@pytest.mark.usefixtures("menuaiio_env")
async def test_read_update_config(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    supervisor_client: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test read and update config."""
    assert await async_setup_component(menuai, "menuaiio", {})
    websocket_client = await menuai_ws_client(menuai)

    await websocket_client.send_json_auto_id({"type": "menuaiio/update/config/info"})
    assert await websocket_client.receive_json() == snapshot

    await websocket_client.send_json_auto_id(
        {
            "type": "menuaiio/update/config/update",
            "add_on_backup_before_update": True,
            "add_on_backup_retain_copies": 2,
            "core_backup_before_update": True,
        }
    )
    assert await websocket_client.receive_json() == snapshot

    await websocket_client.send_json_auto_id({"type": "menuaiio/update/config/info"})
    assert await websocket_client.receive_json() == snapshot
