"""Tests for the Synology DSM backup agent."""

from io import StringIO
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from synology_dsm.api.file_station.models import SynoFileFile, SynoFileSharedFolder
from synology_dsm.exceptions import (
    SynologyDSMAPIErrorException,
    SynologyDSMRequestException,
)

from menuai.components.backup import (
    DOMAIN as BACKUP_DOMAIN,
    AddonInfo,
    AgentBackup,
    Folder,
)
from menuai.components.synology_dsm.const import (
    CONF_BACKUP_PATH,
    CONF_BACKUP_SHARE,
    DOMAIN,
)
from menuai.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.helpers.backup import async_initialize_backup
from menuai.setup import async_setup_component
from menuai.util.aiohttp import MockStreamReader, MockStreamReaderChunked

from .common import mock_dsm_information
from .consts import HOST, MACS, PASSWORD, PORT, USE_SSL, USERNAME

from tests.common import MockConfigEntry
from tests.typing import ClientSessionGenerator, WebSocketGenerator

BASE_FILENAME = "Automatic_backup_2025.2.0.dev0_2025-01-09_20.14_35457323"


async def _mock_download_file(path: str, filename: str) -> MockStreamReader:
    if filename == f"{BASE_FILENAME}_meta.json":
        return MockStreamReader(
            b'{"addons":[],"backup_id":"abcd12ef","date":"2025-01-09T20:14:35.457323+01:00",'
            b'"database_included":true,"extra_metadata":{"instance_id":"36b3b7e984da43fc89f7bafb2645fa36",'
            b'"with_automatic_settings":true},"folders":[],"menuai_included":true,'
            b'"menuai_version":"2025.2.0.dev0","name":"Automatic backup 2025.2.0.dev0","protected":true,"size":13916160}'
        )
    if filename == f"{BASE_FILENAME}.tar":
        return MockStreamReaderChunked(b"backup data")
    raise MockStreamReaderChunked(b"")


async def _mock_download_file_meta_ok_tar_missing(
    path: str, filename: str
) -> MockStreamReader:
    if filename == f"{BASE_FILENAME}_meta.json":
        return MockStreamReader(
            b'{"addons":[],"backup_id":"abcd12ef","date":"2025-01-09T20:14:35.457323+01:00",'
            b'"database_included":true,"extra_metadata":{"instance_id":"36b3b7e984da43fc89f7bafb2645fa36",'
            b'"with_automatic_settings":true},"folders":[],"menuai_included":true,'
            b'"menuai_version":"2025.2.0.dev0","name":"Automatic backup 2025.2.0.dev0","protected":true,"size":13916160}'
        )
    if filename == f"{BASE_FILENAME}.tar":
        raise SynologyDSMAPIErrorException("api", "900", [{"code": 408}])
    raise MockStreamReaderChunked(b"")


async def _mock_download_file_meta_defect(path: str, filename: str) -> MockStreamReader:
    if filename == f"{BASE_FILENAME}_meta.json":
        return MockStreamReader(b"im not a json")
    if filename == f"{BASE_FILENAME}.tar":
        return MockStreamReaderChunked(b"backup data")
    raise MockStreamReaderChunked(b"")


@pytest.fixture
def mock_dsm_with_filestation():
    """Mock a successful service with filestation support."""
    with patch("menuai.components.synology_dsm.common.SynologyDSM") as dsm:
        dsm.login = AsyncMock(return_value=True)
        dsm.update = AsyncMock(return_value=True)

        dsm.surveillance_station.update = AsyncMock(return_value=True)
        dsm.upgrade.update = AsyncMock(return_value=True)
        dsm.utilisation = Mock(cpu_user_load=1, update=AsyncMock(return_value=True))
        dsm.network = Mock(update=AsyncMock(return_value=True), macs=MACS)
        dsm.storage = Mock(
            disks_ids=["sda", "sdb", "sdc"],
            volumes_ids=["volume_1"],
            update=AsyncMock(return_value=True),
        )
        dsm.information = mock_dsm_information()
        dsm.file = AsyncMock(
            get_shared_folders=AsyncMock(
                return_value=[
                    SynoFileSharedFolder(
                        additional=None,
                        is_dir=True,
                        name="HA Backup",
                        path="/ha_backup",
                    )
                ]
            ),
            get_files=AsyncMock(
                return_value=[
                    SynoFileFile(
                        additional=None,
                        is_dir=False,
                        name=f"{BASE_FILENAME}_meta.json",
                        path=f"/ha_backup/my_backup_path/{BASE_FILENAME}_meta.json",
                    ),
                    SynoFileFile(
                        additional=None,
                        is_dir=False,
                        name=f"{BASE_FILENAME}.tar",
                        path=f"/ha_backup/my_backup_path/{BASE_FILENAME}.tar",
                    ),
                ]
            ),
            download_file=_mock_download_file,
            upload_file=AsyncMock(return_value=True),
            delete_file=AsyncMock(return_value=True),
        )
        dsm.logout = AsyncMock(return_value=True)
        yield dsm


@pytest.fixture
def mock_dsm_without_filestation():
    """Mock a successful service with filestation support."""

    with patch("menuai.components.synology_dsm.common.SynologyDSM") as dsm:
        dsm.login = AsyncMock(return_value=True)
        dsm.update = AsyncMock(return_value=True)

        dsm.surveillance_station.update = AsyncMock(return_value=True)
        dsm.upgrade.update = AsyncMock(return_value=True)
        dsm.utilisation = Mock(cpu_user_load=1, update=AsyncMock(return_value=True))
        dsm.network = Mock(update=AsyncMock(return_value=True), macs=MACS)
        dsm.information = mock_dsm_information()
        dsm.storage = Mock(
            disks_ids=["sda", "sdb", "sdc"],
            volumes_ids=["volume_1"],
            update=AsyncMock(return_value=True),
        )
        dsm.file = None

        yield dsm


@pytest.fixture
async def setup_dsm_with_filestation(
    menuai: menuai,
    mock_dsm_with_filestation: MagicMock,
):
    """Mock setup of synology dsm config entry and backup integration."""
    async_initialize_backup(menuai)
    with (
        patch(
            "menuai.components.synology_dsm.common.SynologyDSM",
            return_value=mock_dsm_with_filestation,
        ),
        patch("menuai.components.synology_dsm.PLATFORMS", return_value=[]),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_SSL: USE_SSL,
                CONF_USERNAME: USERNAME,
                CONF_PASSWORD: PASSWORD,
                CONF_MAC: MACS[0],
            },
            options={
                CONF_BACKUP_PATH: "my_backup_path",
                CONF_BACKUP_SHARE: "/ha_backup",
            },
            unique_id="mocked_syno_dsm_entry",
        )
        entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        assert await async_setup_component(menuai, BACKUP_DOMAIN, {BACKUP_DOMAIN: {}})
        await menuai.async_block_till_done()

        yield mock_dsm_with_filestation


async def test_agents_info(
    menuai: menuai,
    setup_dsm_with_filestation: MagicMock,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test backup agent info."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agents": [
            {"agent_id": "synology_dsm.mocked_syno_dsm_entry", "name": "Mock Title"},
            {"agent_id": "backup.local", "name": "local"},
        ],
    }


async def test_agents_not_loaded(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test backup agent with no loaded config entry."""
    with patch("menuai.components.backup.is_menuaiio", return_value=False):
        async_initialize_backup(menuai)
        assert await async_setup_component(menuai, BACKUP_DOMAIN, {BACKUP_DOMAIN: {}})
        assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()
        client = await menuai_ws_client(menuai)

        await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agents": [
            {"agent_id": "backup.local", "name": "local"},
        ],
    }


async def test_agents_on_unload(
    menuai: menuai,
    setup_dsm_with_filestation: MagicMock,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test backup agent on un-loading config entry."""
    # config entry is loaded
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agents": [
            {"agent_id": "synology_dsm.mocked_syno_dsm_entry", "name": "Mock Title"},
            {"agent_id": "backup.local", "name": "local"},
        ],
    }

    # unload config entry
    entries = menuai.config_entries.async_loaded_entries(DOMAIN)
    await menuai.config_entries.async_unload(entries[0].entry_id)
    await menuai.async_block_till_done(wait_background_tasks=True)

    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agents": [
            {"agent_id": "backup.local", "name": "local"},
        ],
    }


async def test_agents_on_changed_update_success(
    menuai: menuai,
    setup_dsm_with_filestation: MagicMock,
    menuai_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test backup agent on changed update success of coordintaor."""
    client = await menuai_ws_client(menuai)

    # config entry is loaded
    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()
    assert response["success"]
    assert len(response["result"]["agents"]) == 2

    # coordinator update was successful
    freezer.tick(910)  # 15 min interval + 10s
    await menuai.async_block_till_done(wait_background_tasks=True)
    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()
    assert response["success"]
    assert len(response["result"]["agents"]) == 2

    # coordinator update was un-successful
    setup_dsm_with_filestation.update.side_effect = SynologyDSMRequestException(
        OSError()
    )
    freezer.tick(910)
    await menuai.async_block_till_done(wait_background_tasks=True)
    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()
    assert response["success"]
    assert len(response["result"]["agents"]) == 1

    # coordinator update was successful again
    setup_dsm_with_filestation.update.side_effect = None
    freezer.tick(910)
    await menuai.async_block_till_done(wait_background_tasks=True)
    await client.send_json_auto_id({"type": "backup/agents/info"})
    response = await client.receive_json()
    assert response["success"]
    assert len(response["result"]["agents"]) == 2


async def test_agents_list_backups(
    menuai: menuai,
    setup_dsm_with_filestation: MagicMock,
    menuai_ws_client: WebSocketGenerator,
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
                "synology_dsm.mocked_syno_dsm_entry": {
                    "protected": True,
                    "size": 13916160,
                }
            },
            "backup_id": "abcd12ef",
            "database_included": True,
            "date": "2025-01-09T20:14:35.457323+01:00",
            "extra_metadata": {"instance_id": ANY, "with_automatic_settings": True},
            "failed_addons": [],
            "failed_agent_ids": [],
            "failed_folders": [],
            "folders": [],
            "menuai_included": True,
            "menuai_version": "2025.2.0.dev0",
            "name": "Automatic backup 2025.2.0.dev0",
            "with_automatic_settings": None,
        }
    ]


async def test_agents_list_backups_error(
    menuai: menuai,
    setup_dsm_with_filestation: MagicMock,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test agent error while list backups."""
    client = await menuai_ws_client(menuai)

    setup_dsm_with_filestation.file.get_files.side_effect = (
        SynologyDSMAPIErrorException("api", "500", "error")
    )

    await client.send_json_auto_id({"type": "backup/info"})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agent_errors": {
            "synology_dsm.mocked_syno_dsm_entry": "Failed to list backups"
        },
        "backups": [],
        "last_attempted_automatic_backup": None,
        "last_completed_automatic_backup": None,
        "last_action_event": None,
        "next_automatic_backup": None,
        "next_automatic_backup_additional": False,
        "state": "idle",
    }


async def test_agents_list_backups_disabled_filestation(
    menuai: menuai,
    mock_dsm_without_filestation: MagicMock,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test agent error while list backups when file station is disabled."""
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id({"type": "backup/info"})
    response = await client.receive_json()

    assert not response["success"]


@pytest.mark.parametrize(
    ("backup_id", "expected_result"),
    [
        (
            "abcd12ef",
            {
                "addons": [],
                "agents": {
                    "synology_dsm.mocked_syno_dsm_entry": {
                        "protected": True,
                        "size": 13916160,
                    }
                },
                "backup_id": "abcd12ef",
                "database_included": True,
                "date": "2025-01-09T20:14:35.457323+01:00",
                "extra_metadata": {"instance_id": ANY, "with_automatic_settings": True},
                "failed_addons": [],
                "failed_agent_ids": [],
                "failed_folders": [],
                "folders": [],
                "menuai_included": True,
                "menuai_version": "2025.2.0.dev0",
                "name": "Automatic backup 2025.2.0.dev0",
                "with_automatic_settings": None,
            },
        ),
        (
            "12345",
            None,
        ),
    ],
    ids=["found", "not_found"],
)
async def test_agents_get_backup(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    setup_dsm_with_filestation: MagicMock,
    backup_id: str,
    expected_result: dict[str, Any] | None,
) -> None:
    """Test agent get backup."""
    client = await menuai_ws_client(menuai)
    await client.send_json_auto_id({"type": "backup/details", "backup_id": backup_id})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"]["agent_errors"] == {}
    assert response["result"]["backup"] == expected_result


async def test_agents_get_backup_not_existing(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    setup_dsm_with_filestation: MagicMock,
) -> None:
    """Test agent get not existing backup."""
    client = await menuai_ws_client(menuai)
    backup_id = "ef34ab12"

    setup_dsm_with_filestation.file.download_file = AsyncMock(
        side_effect=SynologyDSMAPIErrorException("api", "404", "not found")
    )

    await client.send_json_auto_id({"type": "backup/details", "backup_id": backup_id})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"agent_errors": {}, "backup": None}


async def test_agents_get_backup_error(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    setup_dsm_with_filestation: MagicMock,
) -> None:
    """Test agent error while get backup."""
    client = await menuai_ws_client(menuai)
    backup_id = "ef34ab12"

    setup_dsm_with_filestation.file.get_files.side_effect = (
        SynologyDSMAPIErrorException("api", "500", "error")
    )

    await client.send_json_auto_id({"type": "backup/details", "backup_id": backup_id})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agent_errors": {
            "synology_dsm.mocked_syno_dsm_entry": "Failed to list backups"
        },
        "backup": None,
    }


async def test_agents_get_backup_defect_meta(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    setup_dsm_with_filestation: MagicMock,
) -> None:
    """Test agent error while get backup."""
    client = await menuai_ws_client(menuai)
    backup_id = "ef34ab12"

    setup_dsm_with_filestation.file.download_file = _mock_download_file_meta_defect

    await client.send_json_auto_id({"type": "backup/details", "backup_id": backup_id})
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"agent_errors": {}, "backup": None}


async def test_agents_download(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    setup_dsm_with_filestation: MagicMock,
) -> None:
    """Test agent download backup."""
    client = await menuai_client()
    backup_id = "abcd12ef"

    resp = await client.get(
        f"/api/backup/download/{backup_id}?agent_id=synology_dsm.mocked_syno_dsm_entry"
    )
    assert resp.status == 200
    assert await resp.content.read() == b"backup data"


async def test_agents_download_not_existing(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    setup_dsm_with_filestation: MagicMock,
) -> None:
    """Test agent download not existing backup."""
    client = await menuai_client()
    backup_id = "abcd12ef"

    setup_dsm_with_filestation.file.download_file = (
        _mock_download_file_meta_ok_tar_missing
    )

    resp = await client.get(
        f"/api/backup/download/{backup_id}?agent_id=synology_dsm.mocked_syno_dsm_entry"
    )
    assert resp.reason == "Internal Server Error"
    assert resp.status == 500


async def test_agents_upload(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
    setup_dsm_with_filestation: MagicMock,
) -> None:
    """Test agent upload backup."""
    client = await menuai_client()
    backup_id = "test-backup"
    test_backup = AgentBackup(
        addons=[AddonInfo(name="Test", slug="test", version="1.0.0")],
        backup_id=backup_id,
        database_included=True,
        date="1970-01-01T00:00:00.000Z",
        extra_metadata={},
        folders=[Folder.MEDIA, Folder.SHARE],
        menuai_included=True,
        menuai_version="2024.12.0",
        name="Test",
        protected=True,
        size=0,
    )
    base_filename = "Test_1970-01-01_00.00_00000000"

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
            "/api/backup/upload?agent_id=synology_dsm.mocked_syno_dsm_entry",
            data={"file": StringIO("test")},
        )

    assert resp.status == 201
    assert f"Uploading backup {backup_id}" in caplog.text
    mock: AsyncMock = setup_dsm_with_filestation.file.upload_file
    assert len(mock.mock_calls) == 2
    assert mock.call_args_list[0].kwargs["filename"] == f"{base_filename}.tar"
    assert mock.call_args_list[0].kwargs["path"] == "/ha_backup/my_backup_path"
    assert mock.call_args_list[1].kwargs["filename"] == f"{base_filename}_meta.json"
    assert mock.call_args_list[1].kwargs["path"] == "/ha_backup/my_backup_path"


async def test_agents_upload_error(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
    setup_dsm_with_filestation: MagicMock,
) -> None:
    """Test agent error while uploading backup."""
    client = await menuai_client()
    backup_id = "test-backup"
    test_backup = AgentBackup(
        addons=[AddonInfo(name="Test", slug="test", version="1.0.0")],
        backup_id=backup_id,
        database_included=True,
        date="1970-01-01T00:00:00.000Z",
        extra_metadata={},
        folders=[Folder.MEDIA, Folder.SHARE],
        menuai_included=True,
        menuai_version="2024.12.0",
        name="Test",
        protected=True,
        size=0,
    )
    base_filename = "Test_1970-01-01_00.00_00000000"

    # fail to upload the tar file
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
        setup_dsm_with_filestation.file.upload_file.side_effect = (
            SynologyDSMAPIErrorException("api", "500", "error")
        )
        resp = await client.post(
            "/api/backup/upload?agent_id=synology_dsm.mocked_syno_dsm_entry",
            data={"file": StringIO("test")},
        )

    assert resp.status == 201
    assert f"Uploading backup {backup_id}" in caplog.text
    assert "Failed to upload backup" in caplog.text
    mock: AsyncMock = setup_dsm_with_filestation.file.upload_file
    assert len(mock.mock_calls) == 1
    assert mock.call_args_list[0].kwargs["filename"] == f"{base_filename}.tar"
    assert mock.call_args_list[0].kwargs["path"] == "/ha_backup/my_backup_path"

    # fail to upload the meta json file
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
        setup_dsm_with_filestation.file.upload_file.side_effect = [
            True,
            SynologyDSMAPIErrorException("api", "500", "error"),
        ]

        resp = await client.post(
            "/api/backup/upload?agent_id=synology_dsm.mocked_syno_dsm_entry",
            data={"file": StringIO("test")},
        )

    assert resp.status == 201
    assert f"Uploading backup {backup_id}" in caplog.text
    assert "Failed to upload backup" in caplog.text
    mock: AsyncMock = setup_dsm_with_filestation.file.upload_file
    assert len(mock.mock_calls) == 3
    assert mock.call_args_list[1].kwargs["filename"] == f"{base_filename}.tar"
    assert mock.call_args_list[1].kwargs["path"] == "/ha_backup/my_backup_path"
    assert mock.call_args_list[2].kwargs["filename"] == f"{base_filename}_meta.json"
    assert mock.call_args_list[2].kwargs["path"] == "/ha_backup/my_backup_path"


async def test_agents_delete(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    setup_dsm_with_filestation: MagicMock,
) -> None:
    """Test agent delete backup."""
    client = await menuai_ws_client(menuai)
    backup_id = "abcd12ef"

    await client.send_json_auto_id(
        {
            "type": "backup/delete",
            "backup_id": backup_id,
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"agent_errors": {}}
    mock: AsyncMock = setup_dsm_with_filestation.file.delete_file
    assert len(mock.mock_calls) == 2
    assert mock.call_args_list[0].kwargs["filename"] == f"{BASE_FILENAME}.tar"
    assert mock.call_args_list[0].kwargs["path"] == "/ha_backup/my_backup_path"
    assert mock.call_args_list[1].kwargs["filename"] == f"{BASE_FILENAME}_meta.json"
    assert mock.call_args_list[1].kwargs["path"] == "/ha_backup/my_backup_path"


async def test_agents_delete_not_existing(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    setup_dsm_with_filestation: MagicMock,
) -> None:
    """Test delete not existing backup."""
    client = await menuai_ws_client(menuai)
    backup_id = "ef34ab12"

    setup_dsm_with_filestation.file.download_file = (
        _mock_download_file_meta_ok_tar_missing
    )
    setup_dsm_with_filestation.file.delete_file = AsyncMock(
        side_effect=SynologyDSMAPIErrorException(
            "api",
            "900",
            [{"code": 408, "path": f"/ha_backup/my_backup_path/{backup_id}.tar"}],
        )
    )

    await client.send_json_auto_id(
        {
            "type": "backup/delete",
            "backup_id": backup_id,
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"agent_errors": {}}


@pytest.mark.parametrize(
    ("error", "expected_log"),
    [
        (
            SynologyDSMAPIErrorException("api", "100", "Unknown error"),
            "{'api': 'api', 'code': '100', 'reason': 'Unknown', 'details': 'Unknown error'}",
        ),
        (
            SynologyDSMAPIErrorException("api", "900", [{"code": 407}]),
            "{'api': 'api', 'code': '900', 'reason': 'Unknown', 'details': [{'code': 407}]",
        ),
        (
            SynologyDSMAPIErrorException("api", "900", [{"code": 417}]),
            "{'api': 'api', 'code': '900', 'reason': 'Unknown', 'details': [{'code': 417}]",
        ),
    ],
)
async def test_agents_delete_error(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    caplog: pytest.LogCaptureFixture,
    setup_dsm_with_filestation: MagicMock,
    error: SynologyDSMAPIErrorException,
    expected_log: str,
) -> None:
    """Test error while delete backup."""
    client = await menuai_ws_client(menuai)

    # error while delete
    backup_id = "abcd12ef"
    setup_dsm_with_filestation.file.delete_file.side_effect = error
    await client.send_json_auto_id(
        {
            "type": "backup/delete",
            "backup_id": backup_id,
        }
    )
    response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {
        "agent_errors": {
            "synology_dsm.mocked_syno_dsm_entry": "Failed to delete backup"
        }
    }
    assert f"Failed to delete backup: {expected_log}" in caplog.text
    mock: AsyncMock = setup_dsm_with_filestation.file.delete_file
    assert len(mock.mock_calls) == 1
    assert mock.call_args_list[0].kwargs["filename"] == f"{BASE_FILENAME}.tar"
    assert mock.call_args_list[0].kwargs["path"] == "/ha_backup/my_backup_path"
