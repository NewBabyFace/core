"""The tests for the menuaiio component."""

from datetime import timedelta
import logging
import os
from typing import Any
from unittest.mock import AsyncMock, patch

from aiohasupervisor import SupervisorError
from aiohasupervisor.models import AddonsStats
import pytest
from voluptuous import Invalid

from menuai.auth.const import GROUP_ID_ADMIN
from menuai.components import frontend, menuaiio
from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.components.menuaiio import (
    ADDONS_COORDINATOR,
    DOMAIN,
    get_core_info,
    get_supervisor_ip,
    hostname_from_addon_slug,
    is_menuaiio as deprecated_is_menuaiio,
)
from menuai.components.menuaiio.config import STORAGE_KEY
from menuai.components.menuaiio.const import REQUEST_REFRESH_DELAY
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.helpers.menuaiio import is_menuaiio
from menuai.helpers.service_info.menuaiio import menuaiioServiceInfo
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    import_and_test_deprecated_constant,
)
from tests.test_util.aiohttp import AiohttpClientMocker

MOCK_ENVIRON = {"SUPERVISOR": "127.0.0.1", "SUPERVISOR_TOKEN": "abcdefgh"}


@pytest.fixture
def extra_os_info():
    """Extra os/info."""
    return {}


@pytest.fixture
def os_info(extra_os_info):
    """Mock os/info."""
    return {
        "json": {
            "result": "ok",
            "data": {"version_latest": "1.0.0", "version": "1.0.0", **extra_os_info},
        }
    }


@pytest.fixture(autouse=True)
def mock_all(
    aioclient_mock: AiohttpClientMocker,
    os_info: AsyncMock,
    store_info: AsyncMock,
    addon_info: AsyncMock,
    addon_stats: AsyncMock,
    addon_changelog: AsyncMock,
    resolution_info: AsyncMock,
) -> None:
    """Mock all setup requests."""
    aioclient_mock.post("http://127.0.0.1/menuai/options", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/supervisor/options", json={"result": "ok"})
    aioclient_mock.get(
        "http://127.0.0.1/info",
        json={
            "result": "ok",
            "data": {
                "supervisor": "222",
                "menuai": "0.110.0",
                "menuaios": "1.2.3",
            },
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
        **os_info,
    )
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/info",
        json={
            "result": "ok",
            "data": {
                "version_latest": "1.0.0",
                "version": "1.0.0",
                "auto_update": True,
                "addons": [
                    {
                        "name": "test",
                        "slug": "test",
                        "state": "stopped",
                        "update_available": False,
                        "version": "1.0.0",
                        "version_latest": "1.0.0",
                        "repository": "core",
                        "icon": False,
                    },
                    {
                        "name": "test2",
                        "slug": "test2",
                        "state": "stopped",
                        "update_available": False,
                        "version": "1.0.0",
                        "version_latest": "1.0.0",
                        "repository": "core",
                        "icon": False,
                    },
                ],
            },
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/core/stats",
        json={
            "result": "ok",
            "data": {
                "cpu_percent": 0.99,
                "memory_usage": 182611968,
                "memory_limit": 3977146368,
                "memory_percent": 4.59,
                "network_rx": 362570232,
                "network_tx": 82374138,
                "blk_read": 46010945536,
                "blk_write": 15051526144,
            },
        },
    )
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/stats",
        json={
            "result": "ok",
            "data": {
                "cpu_percent": 0.99,
                "memory_usage": 182611968,
                "memory_limit": 3977146368,
                "memory_percent": 4.59,
                "network_rx": 362570232,
                "network_tx": 82374138,
                "blk_read": 46010945536,
                "blk_write": 15051526144,
            },
        },
    )

    async def mock_addon_stats(addon: str) -> AddonsStats:
        """Mock addon stats for test and test2."""
        if addon in {"test2", "test3"}:
            return AddonsStats(
                cpu_percent=0.8,
                memory_usage=51941376,
                memory_limit=3977146368,
                memory_percent=1.31,
                network_rx=31338284,
                network_tx=15692900,
                blk_read=740077568,
                blk_write=6004736,
            )
        return AddonsStats(
            cpu_percent=0.99,
            memory_usage=182611968,
            memory_limit=3977146368,
            memory_percent=4.59,
            network_rx=362570232,
            network_tx=82374138,
            blk_read=46010945536,
            blk_write=15051526144,
        )

    addon_stats.side_effect = mock_addon_stats

    def mock_addon_info(slug: str):
        addon_info.return_value.auto_update = slug == "test"
        return addon_info.return_value

    addon_info.side_effect = mock_addon_info
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


async def test_setup_api_ping(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    supervisor_client: AsyncMock,
) -> None:
    """Test setup with API ping."""
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(menuai, "menuaiio", {})
        await menuai.async_block_till_done()

    assert result
    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 18
    assert get_core_info(menuai)["version_latest"] == "1.0.0"
    assert is_menuaiio(menuai)


async def test_setup_api_panel(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with API ping."""
    assert await async_setup_component(menuai, "frontend", {})
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(menuai, "menuaiio", {})
        assert result

    panels = menuai.data[frontend.DATA_PANELS]

    assert panels.get("menuaiio").to_response() == {
        "component_name": "custom",
        "icon": None,
        "title": None,
        "url_path": "menuaiio",
        "require_admin": True,
        "config_panel_domain": None,
        "config": {
            "_panel_custom": {
                "embed_iframe": True,
                "js_url": "/api/menuaiio/app/entrypoint.js",
                "name": "menuaiio-main",
                "trust_external": False,
            }
        },
    }


async def test_setup_api_push_api_data(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    supervisor_client: AsyncMock,
) -> None:
    """Test setup with API push."""
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            menuai, "menuaiio", {"http": {"server_port": 9999}, "menuaiio": {}}
        )
        await menuai.async_block_till_done()

    assert result
    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 18
    assert not aioclient_mock.mock_calls[0][2]["ssl"]
    assert aioclient_mock.mock_calls[0][2]["port"] == 9999
    assert "watchdog" not in aioclient_mock.mock_calls[0][2]


async def test_setup_api_push_api_data_server_host(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    supervisor_client: AsyncMock,
) -> None:
    """Test setup with API push with active server host."""
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(
            menuai,
            "menuaiio",
            {"http": {"server_port": 9999, "server_host": "127.0.0.1"}, "menuaiio": {}},
        )
        await menuai.async_block_till_done()

    assert result
    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 18
    assert not aioclient_mock.mock_calls[0][2]["ssl"]
    assert aioclient_mock.mock_calls[0][2]["port"] == 9999
    assert not aioclient_mock.mock_calls[0][2]["watchdog"]


async def test_setup_api_push_api_data_default(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    menuai_storage: dict[str, Any],
    supervisor_client: AsyncMock,
) -> None:
    """Test setup with API push default data."""
    with (
        patch.dict(os.environ, MOCK_ENVIRON),
        patch("menuai.components.menuaiio.config.STORE_DELAY_SAVE", 0),
    ):
        result = await async_setup_component(menuai, "menuaiio", {"http": {}, "menuaiio": {}})
        await menuai.async_block_till_done()

    assert result
    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 18
    assert not aioclient_mock.mock_calls[0][2]["ssl"]
    assert aioclient_mock.mock_calls[0][2]["port"] == 8123
    refresh_token = aioclient_mock.mock_calls[0][2]["refresh_token"]
    menuaiio_user = await menuai.auth.async_get_user(
        menuai_storage[STORAGE_KEY]["data"]["menuaiio_user"]
    )
    assert menuaiio_user is not None
    assert menuaiio_user.system_generated
    assert len(menuaiio_user.groups) == 1
    assert menuaiio_user.groups[0].id == GROUP_ID_ADMIN
    assert menuaiio_user.name == "Supervisor"
    for token in menuaiio_user.refresh_tokens.values():
        if token.token == refresh_token:
            break
    else:
        pytest.fail("refresh token not found")


async def test_setup_adds_admin_group_to_user(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    menuai_storage: dict[str, Any],
) -> None:
    """Test setup with API push default data."""
    # Create user without admin
    user = await menuai.auth.async_create_system_user("menuai.io")
    assert not user.is_admin
    await menuai.auth.async_create_refresh_token(user)

    menuai_storage[STORAGE_KEY] = {
        "data": {"menuaiio_user": user.id},
        "key": STORAGE_KEY,
        "version": 1,
    }

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(menuai, "menuaiio", {"http": {}, "menuaiio": {}})
        assert result

    assert user.is_admin


async def test_setup_migrate_user_name(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    menuai_storage: dict[str, Any],
) -> None:
    """Test setup with migrating the user name."""
    # Create user with old name
    user = await menuai.auth.async_create_system_user("menuai.io")
    await menuai.auth.async_create_refresh_token(user)

    menuai_storage[STORAGE_KEY] = {
        "data": {"menuaiio_user": user.id},
        "key": STORAGE_KEY,
        "version": 1,
    }

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(menuai, "menuaiio", {"http": {}, "menuaiio": {}})
        assert result

    assert user.name == "Supervisor"


async def test_setup_api_existing_menuaiio_user(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    menuai_storage: dict[str, Any],
    supervisor_client: AsyncMock,
) -> None:
    """Test setup with API push default data."""
    user = await menuai.auth.async_create_system_user("menuai.io test")
    token = await menuai.auth.async_create_refresh_token(user)
    menuai_storage[STORAGE_KEY] = {"version": 1, "data": {"menuaiio_user": user.id}}
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(menuai, "menuaiio", {"http": {}, "menuaiio": {}})
        await menuai.async_block_till_done()

    assert result
    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 18
    assert not aioclient_mock.mock_calls[0][2]["ssl"]
    assert aioclient_mock.mock_calls[0][2]["port"] == 8123
    assert aioclient_mock.mock_calls[0][2]["refresh_token"] == token.token


async def test_setup_core_push_config(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    supervisor_client: AsyncMock,
) -> None:
    """Test setup with API push default data."""
    menuai.config.time_zone = "testzone"

    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(menuai, "menuaiio", {"menuaiio": {}})
        await menuai.async_block_till_done()

    assert result
    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 18
    assert aioclient_mock.mock_calls[1][2]["timezone"] == "testzone"

    with patch("menuai.util.dt.set_default_time_zone"):
        await menuai.config.async_update(time_zone="America/New_York", country="US")
    await menuai.async_block_till_done()
    assert aioclient_mock.mock_calls[-1][2]["timezone"] == "America/New_York"
    assert aioclient_mock.mock_calls[-1][2]["country"] == "US"


async def test_setup_menuaiio_no_additional_data(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    supervisor_client: AsyncMock,
) -> None:
    """Test setup with API push default data."""
    with (
        patch.dict(os.environ, MOCK_ENVIRON),
        patch.dict(os.environ, {"SUPERVISOR_TOKEN": "123456"}),
    ):
        result = await async_setup_component(menuai, "menuaiio", {"menuaiio": {}})
        await menuai.async_block_till_done()

    assert result
    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 18
    assert aioclient_mock.mock_calls[-1][3]["Authorization"] == "Bearer 123456"


async def test_fail_setup_without_environ_var(menuai: menuai) -> None:
    """Fail setup if no environ variable set."""
    with patch.dict(os.environ, {}, clear=True):
        result = await async_setup_component(menuai, "menuaiio", {})
        assert not result


async def test_warn_when_cannot_connect(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    supervisor_is_connected: AsyncMock,
) -> None:
    """Fail warn when we cannot connect."""
    supervisor_is_connected.side_effect = SupervisorError
    with patch.dict(os.environ, MOCK_ENVIRON):
        result = await async_setup_component(menuai, "menuaiio", {})
        assert result

    assert is_menuaiio(menuai)
    assert "Not connected with the supervisor / system too busy!" in caplog.text


@pytest.mark.usefixtures("menuaiio_env")
async def test_service_register(menuai: menuai) -> None:
    """Check if service will be setup."""
    assert await async_setup_component(menuai, "menuaiio", {})
    assert menuai.services.has_service("menuaiio", "addon_start")
    assert menuai.services.has_service("menuaiio", "addon_stop")
    assert menuai.services.has_service("menuaiio", "addon_restart")
    assert menuai.services.has_service("menuaiio", "addon_stdin")
    assert menuai.services.has_service("menuaiio", "host_shutdown")
    assert menuai.services.has_service("menuaiio", "host_reboot")
    assert menuai.services.has_service("menuaiio", "host_reboot")
    assert menuai.services.has_service("menuaiio", "backup_full")
    assert menuai.services.has_service("menuaiio", "backup_partial")
    assert menuai.services.has_service("menuaiio", "restore_full")
    assert menuai.services.has_service("menuaiio", "restore_partial")


@pytest.mark.freeze_time("2021-11-13 11:48:00")
async def test_service_calls(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
    supervisor_client: AsyncMock,
    addon_installed: AsyncMock,
    supervisor_is_connected: AsyncMock,
) -> None:
    """Call service and check the API calls behind that."""
    supervisor_is_connected.side_effect = SupervisorError
    with patch.dict(os.environ, MOCK_ENVIRON):
        assert await async_setup_component(menuai, "menuaiio", {})
        await menuai.async_block_till_done()

    aioclient_mock.post("http://127.0.0.1/addons/test/start", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/addons/test/stop", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/addons/test/restart", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/addons/test/update", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/addons/test/stdin", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/host/shutdown", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/host/reboot", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/backups/new/full", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/backups/new/partial", json={"result": "ok"})
    aioclient_mock.post(
        "http://127.0.0.1/backups/test/restore/full", json={"result": "ok"}
    )
    aioclient_mock.post(
        "http://127.0.0.1/backups/test/restore/partial", json={"result": "ok"}
    )

    await menuai.services.async_call("menuaiio", "addon_start", {"addon": "test"})
    await menuai.services.async_call("menuaiio", "addon_stop", {"addon": "test"})
    await menuai.services.async_call("menuaiio", "addon_restart", {"addon": "test"})
    await menuai.services.async_call(
        "menuaiio", "addon_stdin", {"addon": "test", "input": "test"}
    )
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 22
    assert aioclient_mock.mock_calls[-1][2] == "test"

    await menuai.services.async_call("menuaiio", "host_shutdown", {})
    await menuai.services.async_call("menuaiio", "host_reboot", {})
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 24

    await menuai.services.async_call("menuaiio", "backup_full", {})
    await menuai.services.async_call(
        "menuaiio",
        "backup_partial",
        {
            "menuai": True,
            "addons": ["test"],
            "folders": ["ssl"],
            "password": "123456",
        },
    )
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 26
    assert aioclient_mock.mock_calls[-1][2] == {
        "name": "2021-11-13 03:48:00",
        "menuai": True,
        "addons": ["test"],
        "folders": ["ssl"],
        "password": "123456",
    }

    await menuai.services.async_call("menuaiio", "restore_full", {"slug": "test"})
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        "menuaiio",
        "restore_partial",
        {
            "slug": "test",
            "menuai": False,
            "addons": ["test"],
            "folders": ["ssl"],
            "password": "123456",
        },
    )
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 28
    assert aioclient_mock.mock_calls[-1][2] == {
        "addons": ["test"],
        "folders": ["ssl"],
        "menuai": False,
        "password": "123456",
    }

    await menuai.services.async_call(
        "menuaiio",
        "backup_full",
        {
            "name": "backup_name",
            "location": "backup_share",
            "menuai_exclude_database": True,
        },
    )
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 29
    assert aioclient_mock.mock_calls[-1][2] == {
        "name": "backup_name",
        "location": "backup_share",
        "menuai_exclude_database": True,
    }

    await menuai.services.async_call(
        "menuaiio",
        "backup_full",
        {
            "location": "/backup",
        },
    )
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 30
    assert aioclient_mock.mock_calls[-1][2] == {
        "name": "2021-11-13 03:48:00",
        "location": None,
    }

    # check backup with different timezone
    await menuai.config.async_update(time_zone="Europe/London")
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        "menuaiio",
        "backup_full",
        {
            "location": "/backup",
        },
    )
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 32
    assert aioclient_mock.mock_calls[-1][2] == {
        "name": "2021-11-13 11:48:00",
        "location": None,
    }


async def test_invalid_service_calls(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    supervisor_is_connected: AsyncMock,
) -> None:
    """Call service with invalid input and check that it raises."""
    supervisor_is_connected.side_effect = SupervisorError
    with patch.dict(os.environ, MOCK_ENVIRON):
        assert await async_setup_component(menuai, "menuaiio", {})
        await menuai.async_block_till_done()

    with pytest.raises(Invalid):
        await menuai.services.async_call(
            "menuaiio", "addon_start", {"addon": "does_not_exist"}
        )
    with pytest.raises(Invalid):
        await menuai.services.async_call(
            "menuaiio", "addon_stdin", {"addon": "does_not_exist", "input": "test"}
        )


async def test_addon_service_call_with_complex_slug(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    supervisor_is_connected: AsyncMock,
) -> None:
    """Addon slugs can have ., - and _, confirm that passes validation."""
    supervisor_mock_data = {
        "version_latest": "1.0.0",
        "version": "1.0.0",
        "auto_update": True,
        "addons": [
            {
                "name": "test.a_1-2",
                "slug": "test.a_1-2",
                "state": "stopped",
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "repository": "core",
                "icon": False,
            },
        ],
    }
    supervisor_is_connected.side_effect = SupervisorError
    with (
        patch.dict(os.environ, MOCK_ENVIRON),
        patch(
            "menuai.components.menuaiio.menuaiIO.get_supervisor_info",
            return_value=supervisor_mock_data,
        ),
    ):
        assert await async_setup_component(menuai, "menuaiio", {})
        await menuai.async_block_till_done()

    await menuai.services.async_call("menuaiio", "addon_start", {"addon": "test.a_1-2"})


@pytest.mark.usefixtures("menuaiio_env")
async def test_service_calls_core(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    supervisor_client: AsyncMock,
) -> None:
    """Call core service and check the API calls behind that."""
    assert await async_setup_component(menuai, "menuai", {})
    assert await async_setup_component(menuai, "menuaiio", {})

    aioclient_mock.post("http://127.0.0.1/menuai/restart", json={"result": "ok"})
    aioclient_mock.post("http://127.0.0.1/menuai/stop", json={"result": "ok"})

    await menuai.services.async_call("menuai", "stop")
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 6

    await menuai.services.async_call("menuai", "check_config")
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 6

    with patch(
        "menuai.config.async_check_ha_config_file", return_value=None
    ) as mock_check_config:
        await menuai.services.async_call("menuai", "restart")
        await menuai.async_block_till_done()
        assert mock_check_config.called

    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 7


@pytest.mark.usefixtures("addon_installed")
async def test_entry_load_and_unload(menuai: menuai) -> None:
    """Test loading and unloading config entry."""
    with patch.dict(os.environ, MOCK_ENVIRON):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert SENSOR_DOMAIN in menuai.config.components
    assert BINARY_SENSOR_DOMAIN in menuai.config.components
    assert ADDONS_COORDINATOR in menuai.data

    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert ADDONS_COORDINATOR not in menuai.data


async def test_migration_off_menuaiio(menuai: menuai) -> None:
    """Test that when a user moves instance off menuai.io, config entry gets cleaned up."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    config_entry.add_to_menuai(menuai)
    assert not await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert menuai.config_entries.async_entries(DOMAIN) == []


@pytest.mark.usefixtures("addon_installed")
async def test_device_registry_calls(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test device registry entries for menuaiio."""
    supervisor_mock_data = {
        "version": "1.0.0",
        "version_latest": "1.0.0",
        "auto_update": True,
        "addons": [
            {
                "name": "test",
                "state": "started",
                "slug": "test",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "repository": "test",
                "url": "https://github.com/home-assistant/addons/test",
            },
            {
                "name": "test2",
                "state": "started",
                "slug": "test2",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "url": "https://github.com",
            },
        ],
    }
    os_mock_data = {
        "board": "odroid-n2",
        "boot": "A",
        "update_available": False,
        "version": "5.12",
        "version_latest": "5.12",
    }

    with (
        patch.dict(os.environ, MOCK_ENVIRON),
        patch(
            "menuai.components.menuaiio.menuaiIO.get_supervisor_info",
            return_value=supervisor_mock_data,
        ),
        patch(
            "menuai.components.menuaiio.menuaiIO.get_os_info",
            return_value=os_mock_data,
        ),
    ):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(device_registry.devices) == 6

    supervisor_mock_data = {
        "version": "1.0.0",
        "version_latest": "1.0.0",
        "auto_update": True,
        "addons": [
            {
                "name": "test2",
                "state": "started",
                "slug": "test2",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "url": "https://github.com",
            },
        ],
    }

    # Test that when addon is removed, next update will remove the add-on and subsequent updates won't
    with (
        patch(
            "menuai.components.menuaiio.menuaiIO.get_supervisor_info",
            return_value=supervisor_mock_data,
        ),
        patch(
            "menuai.components.menuaiio.menuaiIO.get_os_info",
            return_value=os_mock_data,
        ),
    ):
        async_fire_time_changed(menuai, dt_util.now() + timedelta(hours=1))
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(device_registry.devices) == 5

        async_fire_time_changed(menuai, dt_util.now() + timedelta(hours=2))
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert len(device_registry.devices) == 5

    supervisor_mock_data = {
        "version": "1.0.0",
        "version_latest": "1.0.0",
        "auto_update": True,
        "addons": [
            {
                "name": "test2",
                "slug": "test2",
                "state": "started",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "url": "https://github.com",
            },
            {
                "name": "test3",
                "slug": "test3",
                "state": "stopped",
                "installed": True,
                "icon": False,
                "update_available": False,
                "version": "1.0.0",
                "version_latest": "1.0.0",
                "url": "https://github.com",
            },
        ],
    }

    # Test that when addon is added, next update will reload the entry so we register
    # a new device
    with (
        patch(
            "menuai.components.menuaiio.menuaiIO.get_supervisor_info",
            return_value=supervisor_mock_data,
        ),
        patch(
            "menuai.components.menuaiio.menuaiIO.get_os_info",
            return_value=os_mock_data,
        ),
        patch(
            "menuai.components.menuaiio.menuaiIO.get_info",
            return_value={
                "supervisor": "222",
                "menuai": "0.110.0",
                "menuaios": None,
            },
        ),
    ):
        async_fire_time_changed(menuai, dt_util.now() + timedelta(hours=3))
        await menuai.async_block_till_done()
        assert len(device_registry.devices) == 5


@pytest.mark.usefixtures("addon_installed")
async def test_coordinator_updates(
    menuai: menuai, caplog: pytest.LogCaptureFixture, supervisor_client: AsyncMock
) -> None:
    """Test coordinator updates."""
    await async_setup_component(menuai, "menuai", {})
    with patch.dict(os.environ, MOCK_ENVIRON):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        # Initial refresh, no update refresh call
        supervisor_client.refresh_updates.assert_not_called()

    async_fire_time_changed(menuai, dt_util.now() + timedelta(minutes=20))
    await menuai.async_block_till_done()

    # Scheduled refresh, no update refresh call
    supervisor_client.refresh_updates.assert_not_called()

    await menuai.services.async_call(
        "menuai",
        "update_entity",
        {
            "entity_id": [
                "update.home_assistant_core_update",
                "update.home_assistant_supervisor_update",
            ]
        },
        blocking=True,
    )

    # There is a REQUEST_REFRESH_DELAYs cooldown on the debouncer
    supervisor_client.refresh_updates.assert_not_called()
    async_fire_time_changed(
        menuai, dt_util.now() + timedelta(seconds=REQUEST_REFRESH_DELAY)
    )
    await menuai.async_block_till_done()
    supervisor_client.refresh_updates.assert_called_once()

    supervisor_client.refresh_updates.reset_mock()
    supervisor_client.refresh_updates.side_effect = SupervisorError("Unknown")
    await menuai.services.async_call(
        "menuai",
        "update_entity",
        {
            "entity_id": [
                "update.home_assistant_core_update",
                "update.home_assistant_supervisor_update",
            ]
        },
        blocking=True,
    )
    # There is a REQUEST_REFRESH_DELAYs cooldown on the debouncer
    async_fire_time_changed(
        menuai, dt_util.now() + timedelta(seconds=REQUEST_REFRESH_DELAY)
    )
    await menuai.async_block_till_done()
    supervisor_client.refresh_updates.assert_called_once()
    assert "Error on Supervisor API: Unknown" in caplog.text


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "addon_installed")
async def test_coordinator_updates_stats_entities_enabled(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    supervisor_client: AsyncMock,
) -> None:
    """Test coordinator updates with stats entities enabled."""
    await async_setup_component(menuai, "menuai", {})
    with patch.dict(os.environ, MOCK_ENVIRON):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
        config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        # Initial refresh without stats
        supervisor_client.refresh_updates.assert_not_called()

        # Refresh with stats once we know which ones are needed
        async_fire_time_changed(
            menuai, dt_util.now() + timedelta(seconds=REQUEST_REFRESH_DELAY)
        )
        await menuai.async_block_till_done()

        supervisor_client.refresh_updates.assert_called_once()

    supervisor_client.refresh_updates.reset_mock()
    async_fire_time_changed(menuai, dt_util.now() + timedelta(minutes=20))
    await menuai.async_block_till_done()
    supervisor_client.refresh_updates.assert_not_called()

    await menuai.services.async_call(
        "menuai",
        "update_entity",
        {
            "entity_id": [
                "update.home_assistant_core_update",
                "update.home_assistant_supervisor_update",
            ]
        },
        blocking=True,
    )
    supervisor_client.refresh_updates.assert_not_called()

    # There is a REQUEST_REFRESH_DELAYs cooldown on the debouncer
    async_fire_time_changed(
        menuai, dt_util.now() + timedelta(seconds=REQUEST_REFRESH_DELAY)
    )
    await menuai.async_block_till_done()

    supervisor_client.refresh_updates.reset_mock()
    supervisor_client.refresh_updates.side_effect = SupervisorError("Unknown")
    await menuai.services.async_call(
        "menuai",
        "update_entity",
        {
            "entity_id": [
                "update.home_assistant_core_update",
                "update.home_assistant_supervisor_update",
            ]
        },
        blocking=True,
    )
    # There is a REQUEST_REFRESH_DELAYs cooldown on the debouncer
    async_fire_time_changed(
        menuai, dt_util.now() + timedelta(seconds=REQUEST_REFRESH_DELAY)
    )
    await menuai.async_block_till_done()
    supervisor_client.refresh_updates.assert_called_once()
    assert "Error on Supervisor API: Unknown" in caplog.text


@pytest.mark.parametrize(
    ("extra_os_info", "integration"),
    [
        ({"board": "green"}, "menuai_green"),
        ({"board": "odroid-c2"}, "hardkernel"),
        ({"board": "odroid-c4"}, "hardkernel"),
        ({"board": "odroid-n2"}, "hardkernel"),
        ({"board": "odroid-xu4"}, "hardkernel"),
        ({"board": "rpi2"}, "raspberry_pi"),
        ({"board": "rpi3"}, "raspberry_pi"),
        ({"board": "rpi3-64"}, "raspberry_pi"),
        ({"board": "rpi4"}, "raspberry_pi"),
        ({"board": "rpi4-64"}, "raspberry_pi"),
        ({"board": "yellow"}, "menuai_yellow"),
    ],
)
async def test_setup_hardware_integration(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    supervisor_client: AsyncMock,
    integration,
) -> None:
    """Test setup initiates hardware integration."""

    with (
        patch.dict(os.environ, MOCK_ENVIRON),
        patch(
            f"menuai.components.{integration}.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await async_setup_component(menuai, "menuaiio", {"menuaiio": {}})
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert result
    assert aioclient_mock.call_count + len(supervisor_client.mock_calls) == 18
    assert len(mock_setup_entry.mock_calls) == 1


def test_hostname_from_addon_slug() -> None:
    """Test hostname_from_addon_slug."""
    assert hostname_from_addon_slug("mqtt") == "mqtt"
    assert (
        hostname_from_addon_slug("core_silabs_multiprotocol")
        == "core-silabs-multiprotocol"
    )


def test_deprecated_function_is_menuaiio(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test calling deprecated_is_menuaiio function will create log entry."""

    deprecated_is_menuaiio(menuai)
    assert caplog.record_tuples == [
        (
            "menuai.components.menuaiio",
            logging.WARNING,
            "is_menuaiio is a deprecated function which will be removed in HA Core 2025.11. Use menuai.helpers.menuaiio.is_menuaiio instead",
        )
    ]


def test_deprecated_function_get_supervisor_ip(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test calling get_supervisor_ip function will create log entry."""

    get_supervisor_ip()
    assert caplog.record_tuples == [
        (
            "menuai.helpers.menuaiio",
            logging.WARNING,
            "get_supervisor_ip is a deprecated function which will be removed in HA Core 2025.11. Use menuai.helpers.menuaiio.get_supervisor_ip instead",
        )
    ]


@pytest.mark.parametrize(
    ("constant_name", "replacement_name", "replacement"),
    [
        (
            "menuaiioServiceInfo",
            "menuai.helpers.service_info.menuaiio.menuaiioServiceInfo",
            menuaiioServiceInfo,
        ),
    ],
)
def test_deprecated_constants(
    caplog: pytest.LogCaptureFixture,
    constant_name: str,
    replacement_name: str,
    replacement: Any,
) -> None:
    """Test deprecated automation constants."""
    import_and_test_deprecated_constant(
        caplog,
        menuaiio,
        constant_name,
        replacement_name,
        replacement,
        "2025.11",
    )
