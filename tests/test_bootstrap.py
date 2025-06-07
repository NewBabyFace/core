"""Test the bootstrapping."""

import asyncio
from collections.abc import Generator, Iterable
import contextlib
import glob
import logging
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from menuai import bootstrap, config as config_util, core, loader, runner
from menuai.config_entries import ConfigEntry
from menuai.const import (
    BASE_PLATFORMS,
    CONF_DEBUG,
    SIGNAL_BOOTSTRAP_INTEGRATIONS,
)
from menuai.core import CoreState, menuai, async_get_menuai, callback
from menuai.exceptions import menuaiError
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.translation import async_translations_loaded
from menuai.helpers.typing import ConfigType
from menuai.loader import Integration

from .common import (
    MockConfigEntry,
    MockModule,
    MockPlatform,
    get_test_config_dir,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

VERSION_PATH = os.path.join(get_test_config_dir(), config_util.VERSION_FILE)


@pytest.fixture(autouse=True)
def disable_installed_check() -> Generator[None]:
    """Disable package installed check."""
    with patch("menuai.util.package.is_installed", return_value=True):
        yield


@pytest.fixture(autouse=True)
def apply_mock_storage(menuai_storage: dict[str, Any]) -> None:
    """Apply the storage mock."""


@pytest.fixture(autouse=True)
async def apply_stop_menuai(stop_menuai: None) -> None:
    """Make sure all menuai are stopped."""


@pytest.fixture(autouse=True)
def disable_block_async_io(disable_block_async_io):
    """Disable the loop protection from block_async_io after each test."""


@pytest.fixture(scope="module", autouse=True)
def mock_http_start_stop() -> Generator[None]:
    """Mock HTTP start and stop."""
    with (
        patch("menuai.components.http.start_http_server_and_save_config"),
        patch("menuai.components.http.menuaiHTTP.stop"),
    ):
        yield


@patch("menuai.bootstrap.async_enable_logging", AsyncMock())
async def test_home_assistant_core_config_validation(menuai: menuai) -> None:
    """Test if we pass in wrong information for HA conf."""
    # Extensive HA conf validation testing is done
    result = await bootstrap.async_from_config_dict(
        {"menuai": {"latitude": "some string"}}, menuai
    )
    assert result is None


async def test_async_enable_logging(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test to ensure logging is migrated to the queue handlers."""
    with (
        patch("logging.getLogger"),
        patch(
            "menuai.bootstrap.async_activate_log_queue_handler"
        ) as mock_async_activate_log_queue_handler,
        patch(
            "menuai.bootstrap.logging.handlers.RotatingFileHandler.doRollover",
            side_effect=OSError,
        ),
    ):
        await bootstrap.async_enable_logging(menuai)
        mock_async_activate_log_queue_handler.assert_called_once()
        mock_async_activate_log_queue_handler.reset_mock()
        await bootstrap.async_enable_logging(
            menuai,
            log_rotate_days=5,
            log_file="test.log",
        )
        mock_async_activate_log_queue_handler.assert_called_once()
        for f in glob.glob("test.log*"):
            os.remove(f)
        for f in glob.glob("testing_config/home-assistant.log*"):
            os.remove(f)

    assert "Error rolling over log file" in caplog.text


async def test_load_menuaiio(menuai: menuai) -> None:
    """Test that we load the menuaiio integration when using Supervisor."""
    with patch.dict(os.environ, {}, clear=True):
        assert "menuaiio" not in bootstrap._get_domains(menuai, {})

    with patch.dict(os.environ, {"SUPERVISOR": "1"}):
        assert "menuaiio" in bootstrap._get_domains(menuai, {})


@pytest.mark.parametrize("load_registries", [False])
async def test_empty_setup(menuai: menuai) -> None:
    """Test an empty set up loads the core."""
    await bootstrap.async_from_config_dict({}, menuai)
    for domain in bootstrap.CORE_INTEGRATIONS:
        assert domain in menuai.config.components, domain


@pytest.mark.parametrize("load_registries", [False])
async def test_config_does_not_turn_off_debug(menuai: menuai) -> None:
    """Test that config does not turn off debug if its turned on by runtime config."""
    # Mock that its turned on from RuntimeConfig
    menuai.config.debug = True

    await bootstrap.async_from_config_dict({CONF_DEBUG: False}, menuai)
    assert menuai.config.debug is True


@pytest.mark.parametrize("menuai_config", [{"frontend": {}}])
@pytest.mark.usefixtures("mock_menuai_config")
async def test_asyncio_debug_on_turns_menuai_debug_on(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
) -> None:
    """Test that asyncio debug turns on menuai debug."""
    asyncio.get_running_loop().set_debug(True)

    verbose = Mock()
    log_rotate_days = Mock()
    log_file = Mock()
    log_no_color = Mock()

    menuai = await bootstrap.async_setup_menuai(
        runner.RuntimeConfig(
            config_dir=get_test_config_dir(),
            verbose=verbose,
            log_rotate_days=log_rotate_days,
            log_file=log_file,
            log_no_color=log_no_color,
            skip_pip=True,
            recovery_mode=False,
        ),
    )

    assert menuai.config.debug is True


@pytest.mark.parametrize("load_registries", [False])
async def test_preload_translations(menuai: menuai) -> None:
    """Test translations are preloaded for all frontend deps and base platforms."""
    await bootstrap.async_from_config_dict({}, menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)
    frontend = await loader.async_get_integration(menuai, "frontend")
    assert async_translations_loaded(menuai, set(frontend.all_dependencies))
    assert async_translations_loaded(menuai, BASE_PLATFORMS)


async def test_core_failure_loads_recovery_mode(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test failing core setup aborts further setup."""
    with patch(
        "menuai.components.menuai.async_setup",
        return_value=False,
    ):
        await bootstrap.async_from_config_dict({"group": {}}, menuai)

    assert "core failed to initialize" in caplog.text
    # We aborted early, group not set up
    assert "group" not in menuai.config.components


@pytest.mark.parametrize("load_registries", [False])
async def test_setting_up_config(menuai: menuai) -> None:
    """Test we set up domains in config."""
    await bootstrap._async_set_up_integrations(
        menuai, {"group hello": {}, "menuai": {}}
    )

    assert "group" in menuai.config.components


@pytest.mark.parametrize("load_registries", [False])
async def test_setup_after_deps_all_present(menuai: menuai) -> None:
    """Test after_dependencies when all present."""
    order = []

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            order.append(domain)
            return True

        return async_setup

    mock_integration(
        menuai, MockModule(domain="root", async_setup=gen_domain_setup("root"))
    )
    mock_integration(
        menuai,
        MockModule(
            domain="first_dep",
            async_setup=gen_domain_setup("first_dep"),
            partial_manifest={"after_dependencies": ["root"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="second_dep",
            async_setup=gen_domain_setup("second_dep"),
            partial_manifest={"after_dependencies": ["first_dep"]},
        ),
    )

    with patch(
        "menuai.components.logger.async_setup", gen_domain_setup("logger")
    ):
        await bootstrap._async_set_up_integrations(
            menuai, {"root": {}, "first_dep": {}, "second_dep": {}, "logger": {}}
        )

    assert "root" in menuai.config.components
    assert "first_dep" in menuai.config.components
    assert "second_dep" in menuai.config.components
    assert order == ["logger", "root", "first_dep", "second_dep"]


@pytest.mark.parametrize("load_registries", [False])
async def test_setup_after_deps_in_stage_1(menuai: menuai) -> None:
    """Test after_dependencies are promoted in stage 1."""
    # This test relies on this
    assert "cloud" in bootstrap.STAGE_1_INTEGRATIONS
    order = []

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            order.append(domain)
            return True

        return async_setup

    mock_integration(
        menuai,
        MockModule(
            domain="normal_integration",
            async_setup=gen_domain_setup("normal_integration"),
            partial_manifest={"after_dependencies": ["an_after_dep"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="an_after_dep",
            async_setup=gen_domain_setup("an_after_dep"),
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="cloud",
            async_setup=gen_domain_setup("cloud"),
            partial_manifest={"after_dependencies": ["normal_integration"]},
        ),
    )

    await bootstrap._async_set_up_integrations(
        menuai, {"cloud": {}, "normal_integration": {}, "an_after_dep": {}}
    )

    assert "normal_integration" in menuai.config.components
    assert "cloud" in menuai.config.components
    assert order == ["an_after_dep", "normal_integration", "cloud"]


@pytest.mark.parametrize("load_registries", [False])
async def test_setup_after_deps_manifests_are_loaded_even_if_not_setup(
    menuai: menuai,
) -> None:
    """Ensure we preload manifests for after deps even if they are not setup.

    It's important that we preload the after dep manifests even if they are not setup
    since we will always have to check their requirements since any integration
    that lists an after dep may import it and we have to ensure requirements are
    up to date before the after dep can be imported.
    """
    # This test relies on this
    assert "cloud" in bootstrap.STAGE_1_INTEGRATIONS
    order = []

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            order.append(domain)
            return True

        return async_setup

    mock_integration(
        menuai,
        MockModule(
            domain="normal_integration",
            async_setup=gen_domain_setup("normal_integration"),
            partial_manifest={"after_dependencies": ["an_after_dep"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="an_after_dep",
            async_setup=gen_domain_setup("an_after_dep"),
            partial_manifest={"after_dependencies": ["an_after_dep_of_after_dep"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="an_after_dep_of_after_dep",
            async_setup=gen_domain_setup("an_after_dep_of_after_dep"),
            partial_manifest={
                "after_dependencies": ["an_after_dep_of_after_dep_of_after_dep"]
            },
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="an_after_dep_of_after_dep_of_after_dep",
            async_setup=gen_domain_setup("an_after_dep_of_after_dep_of_after_dep"),
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="cloud",
            async_setup=gen_domain_setup("cloud"),
            partial_manifest={"after_dependencies": ["normal_integration"]},
        ),
    )

    await bootstrap._async_set_up_integrations(
        menuai, {"cloud": {}, "normal_integration": {}}
    )

    assert "normal_integration" in menuai.config.components
    assert "cloud" in menuai.config.components
    assert "an_after_dep" not in menuai.config.components
    assert "an_after_dep_of_after_dep" not in menuai.config.components
    assert "an_after_dep_of_after_dep_of_after_dep" not in menuai.config.components
    assert order == ["normal_integration", "cloud"]
    assert loader.async_get_loaded_integration(menuai, "an_after_dep") is not None
    assert (
        loader.async_get_loaded_integration(menuai, "an_after_dep_of_after_dep")
        is not None
    )
    assert (
        loader.async_get_loaded_integration(
            menuai, "an_after_dep_of_after_dep_of_after_dep"
        )
        is not None
    )


@pytest.mark.parametrize("load_registries", [False])
async def test_setup_frontend_before_recorder(menuai: menuai) -> None:
    """Test frontend is setup before recorder."""
    order = []

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            order.append(domain)
            return True

        return async_setup

    mock_integration(
        menuai,
        MockModule(
            domain="normal_integration",
            async_setup=gen_domain_setup("normal_integration"),
            partial_manifest={"after_dependencies": ["an_after_dep"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="an_after_dep",
            async_setup=gen_domain_setup("an_after_dep"),
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="frontend",
            async_setup=gen_domain_setup("frontend"),
            partial_manifest={
                "dependencies": ["http"],
                "after_dependencies": ["an_after_dep"],
            },
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="http",
            async_setup=gen_domain_setup("http"),
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="recorder",
            async_setup=gen_domain_setup("recorder"),
        ),
    )

    await bootstrap._async_set_up_integrations(
        menuai,
        {
            "frontend": {},
            "http": {},
            "recorder": {},
            "normal_integration": {},
            "an_after_dep": {},
        },
    )

    assert "frontend" in menuai.config.components
    assert "normal_integration" in menuai.config.components
    assert "recorder" in menuai.config.components
    assert "http" in menuai.config.components

    assert order == [
        "http",
        "an_after_dep",
        "frontend",
        "recorder",
        "normal_integration",
    ]


@pytest.mark.parametrize("load_registries", [False])
async def test_setup_after_deps_via_platform(menuai: menuai) -> None:
    """Test after_dependencies set up via platform."""
    order = []
    after_dep_event = asyncio.Event()

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            if domain == "after_dep_of_platform_int":
                await after_dep_event.wait()

            order.append(domain)
            return True

        return async_setup

    mock_integration(
        menuai,
        MockModule(
            domain="after_dep_of_platform_int",
            async_setup=gen_domain_setup("after_dep_of_platform_int"),
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="platform_int",
            async_setup=gen_domain_setup("platform_int"),
            partial_manifest={"after_dependencies": ["after_dep_of_platform_int"]},
        ),
    )
    mock_platform(menuai, "platform_int.light", MockPlatform())

    @callback
    def continue_loading(_):
        """When light component loaded, continue other loading."""
        after_dep_event.set()

    menuai.bus.async_listen_once("component_loaded", continue_loading)

    await bootstrap._async_set_up_integrations(
        menuai, {"light": {"platform": "platform_int"}, "after_dep_of_platform_int": {}}
    )

    assert "light" in menuai.config.components
    assert "after_dep_of_platform_int" in menuai.config.components
    assert "platform_int" in menuai.config.components
    assert order == ["after_dep_of_platform_int", "platform_int"]


@pytest.mark.parametrize("load_registries", [False])
async def test_setup_after_deps_not_trigger_load(menuai: menuai) -> None:
    """Test after_dependencies does not trigger loading it."""
    order = []

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            order.append(domain)
            return True

        return async_setup

    mock_integration(
        menuai, MockModule(domain="root", async_setup=gen_domain_setup("root"))
    )
    mock_integration(
        menuai,
        MockModule(
            domain="first_dep",
            async_setup=gen_domain_setup("first_dep"),
            partial_manifest={"after_dependencies": ["root"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="second_dep",
            async_setup=gen_domain_setup("second_dep"),
            partial_manifest={"after_dependencies": ["first_dep"]},
        ),
    )

    await bootstrap._async_set_up_integrations(menuai, {"root": {}, "second_dep": {}})

    assert "root" in menuai.config.components
    assert "first_dep" not in menuai.config.components
    assert "second_dep" in menuai.config.components


@pytest.mark.parametrize("load_registries", [False])
async def test_setup_after_deps_not_present(menuai: menuai) -> None:
    """Test after_dependencies when referenced integration doesn't exist."""
    order = []

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            order.append(domain)
            return True

        return async_setup

    mock_integration(
        menuai, MockModule(domain="root", async_setup=gen_domain_setup("root"))
    )
    mock_integration(
        menuai,
        MockModule(
            domain="second_dep",
            async_setup=gen_domain_setup("second_dep"),
            partial_manifest={"after_dependencies": ["first_dep", "root"]},
        ),
    )

    await bootstrap._async_set_up_integrations(
        menuai, {"root": {}, "first_dep": {}, "second_dep": {}}
    )

    assert "root" in menuai.config.components
    assert "first_dep" not in menuai.config.components
    assert "second_dep" in menuai.config.components
    assert order == ["root", "second_dep"]


@pytest.fixture
def mock_is_virtual_env() -> Generator[Mock]:
    """Mock is_virtual_env."""
    with patch(
        "menuai.bootstrap.is_virtual_env", return_value=False
    ) as is_virtual_env:
        yield is_virtual_env


@pytest.fixture
def mock_enable_logging() -> Generator[AsyncMock]:
    """Mock enable logging."""
    with patch("menuai.bootstrap.async_enable_logging") as enable_logging:
        yield enable_logging


@pytest.fixture
def mock_mount_local_lib_path() -> Generator[AsyncMock]:
    """Mock enable logging."""
    with patch(
        "menuai.bootstrap.async_mount_local_lib_path"
    ) as mount_local_lib_path:
        yield mount_local_lib_path


@pytest.fixture
def mock_process_ha_config_upgrade() -> Generator[Mock]:
    """Mock enable logging."""
    with patch(
        "menuai.config.process_ha_config_upgrade"
    ) as process_ha_config_upgrade:
        yield process_ha_config_upgrade


@pytest.fixture
def mock_ensure_config_exists() -> Generator[AsyncMock]:
    """Mock enable logging."""
    with patch(
        "menuai.config.async_ensure_config_exists", return_value=True
    ) as ensure_config_exists:
        yield ensure_config_exists


@pytest.mark.parametrize("menuai_config", [{"browser": {}, "frontend": {}}])
@pytest.mark.usefixtures("mock_menuai_config")
async def test_setup_menuai(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test it works."""
    verbose = Mock()
    log_rotate_days = Mock()
    log_file = Mock()
    log_no_color = Mock()

    with patch.object(bootstrap, "LOG_SLOW_STARTUP_INTERVAL", 5000):
        menuai = await bootstrap.async_setup_menuai(
            runner.RuntimeConfig(
                config_dir=get_test_config_dir(),
                verbose=verbose,
                log_rotate_days=log_rotate_days,
                log_file=log_file,
                log_no_color=log_no_color,
                skip_pip=True,
                recovery_mode=False,
                debug=True,
            ),
        )

    assert "Waiting on integrations to complete setup" not in caplog.text

    assert "browser" in menuai.config.components
    assert "recovery_mode" not in menuai.config.components

    assert len(mock_enable_logging.mock_calls) == 1
    assert mock_enable_logging.mock_calls[0][1] == (
        menuai,
        verbose,
        log_rotate_days,
        log_file,
        log_no_color,
    )
    assert len(mock_mount_local_lib_path.mock_calls) == 1
    assert len(mock_ensure_config_exists.mock_calls) == 1
    assert len(mock_process_ha_config_upgrade.mock_calls) == 1

    # debug in RuntimeConfig should set it it in menuai.config
    assert menuai.config.debug is True

    assert menuai == async_get_menuai()


@pytest.mark.parametrize("menuai_config", [{"browser": {}, "frontend": {}}])
@pytest.mark.usefixtures("mock_menuai_config")
async def test_setup_menuai_takes_longer_than_log_slow_startup(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test it works."""
    verbose = Mock()
    log_rotate_days = Mock()
    log_file = Mock()
    log_no_color = Mock()

    async def _async_setup_that_blocks_startup(*args, **kwargs):
        await asyncio.sleep(0.2)
        return True

    with (
        patch.object(bootstrap, "LOG_SLOW_STARTUP_INTERVAL", 0.005),
        patch.object(bootstrap, "SLOW_STARTUP_CHECK_INTERVAL", 0.005),
        patch(
            "menuai.components.frontend.async_setup",
            side_effect=_async_setup_that_blocks_startup,
        ),
    ):
        await bootstrap.async_setup_menuai(
            runner.RuntimeConfig(
                config_dir=get_test_config_dir(),
                verbose=verbose,
                log_rotate_days=log_rotate_days,
                log_file=log_file,
                log_no_color=log_no_color,
                skip_pip=True,
                recovery_mode=False,
            ),
        )

    assert "Waiting on integrations to complete setup" in caplog.text


async def test_setup_menuai_invalid_yaml(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
) -> None:
    """Test it works."""
    with patch(
        "menuai.config.async_menuai_config_yaml", side_effect=menuaiError
    ):
        menuai = await bootstrap.async_setup_menuai(
            runner.RuntimeConfig(
                config_dir=get_test_config_dir(),
                verbose=False,
                log_rotate_days=10,
                log_file="",
                log_no_color=False,
                skip_pip=True,
                recovery_mode=False,
            ),
        )

    assert "recovery_mode" in menuai.config.components
    assert len(mock_mount_local_lib_path.mock_calls) == 0


async def test_setup_menuai_config_dir_nonexistent(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
) -> None:
    """Test it works."""
    mock_ensure_config_exists.return_value = False

    assert (
        await bootstrap.async_setup_menuai(
            runner.RuntimeConfig(
                config_dir=get_test_config_dir(),
                verbose=False,
                log_rotate_days=10,
                log_file="",
                log_no_color=False,
                skip_pip=True,
                recovery_mode=False,
            ),
        )
        is None
    )


async def test_setup_menuai_recovery_mode(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
) -> None:
    """Test it works."""
    with (
        patch(
            "menuai.core.menuai", wraps=core.menuai
        ) as mock_menuai,
        patch("menuai.components.browser.setup") as browser_setup,
        patch(
            "menuai.config_entries.ConfigEntries.async_domains",
            return_value=["browser"],
        ),
    ):
        menuai = await bootstrap.async_setup_menuai(
            runner.RuntimeConfig(
                config_dir=get_test_config_dir(),
                verbose=False,
                log_rotate_days=10,
                log_file="",
                log_no_color=False,
                skip_pip=True,
                recovery_mode=True,
            ),
        )

    mock_menuai.assert_called_once()

    assert "recovery_mode" in menuai.config.components
    assert len(mock_mount_local_lib_path.mock_calls) == 0

    # Validate we didn't try to set up config entry.
    assert "browser" not in menuai.config.components
    assert len(browser_setup.mock_calls) == 0


@pytest.mark.usefixtures("mock_menuai_config")
async def test_setup_menuai_safe_mode(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test it works."""
    with (
        patch("menuai.components.browser.setup"),
        patch(
            "menuai.config_entries.ConfigEntries.async_domains",
            return_value=["browser"],
        ),
    ):
        menuai = await bootstrap.async_setup_menuai(
            runner.RuntimeConfig(
                config_dir=get_test_config_dir(),
                verbose=False,
                log_rotate_days=10,
                log_file="",
                log_no_color=False,
                skip_pip=True,
                recovery_mode=False,
                safe_mode=True,
            ),
        )

    assert "recovery_mode" not in menuai.config.components
    assert "Starting in recovery mode" not in caplog.text
    assert "Starting in safe mode" in caplog.text


@pytest.mark.usefixtures("mock_menuai_config")
async def test_setup_menuai_recovery_mode_and_safe_mode(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test it works."""
    with (
        patch("menuai.components.browser.setup"),
        patch(
            "menuai.config_entries.ConfigEntries.async_domains",
            return_value=["browser"],
        ),
    ):
        menuai = await bootstrap.async_setup_menuai(
            runner.RuntimeConfig(
                config_dir=get_test_config_dir(),
                verbose=False,
                log_rotate_days=10,
                log_file="",
                log_no_color=False,
                skip_pip=True,
                recovery_mode=True,
                safe_mode=True,
            ),
        )

    assert "recovery_mode" in menuai.config.components
    assert "Starting in recovery mode" in caplog.text
    assert "Starting in safe mode" not in caplog.text


@pytest.mark.parametrize("menuai_config", [{"menuai": {"non-existing": 1}}])
@pytest.mark.usefixtures("mock_menuai_config")
async def test_setup_menuai_invalid_core_config(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
) -> None:
    """Test it works."""
    with patch("menuai.bootstrap.async_notify_setup_error") as mock_notify:
        menuai = await bootstrap.async_setup_menuai(
            runner.RuntimeConfig(
                config_dir=get_test_config_dir(),
                verbose=False,
                log_rotate_days=10,
                log_file="",
                log_no_color=False,
                skip_pip=True,
                recovery_mode=False,
            ),
        )
        assert len(mock_notify.mock_calls) == 1

    assert "recovery_mode" in menuai.config.components


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            "menuai": {
                "internal_url": "http://192.168.1.100:8123",
                "external_url": "https://abcdef.ui.nabu.casa",
            },
            "map": {},
            "frontend": {"invalid": True},
        }
    ],
)
@pytest.mark.usefixtures("mock_menuai_config")
async def test_setup_recovery_mode_if_no_frontend(
    mock_enable_logging: AsyncMock,
    mock_is_virtual_env: Mock,
    mock_mount_local_lib_path: AsyncMock,
    mock_ensure_config_exists: AsyncMock,
    mock_process_ha_config_upgrade: Mock,
) -> None:
    """Test we setup recovery mode if frontend didn't load."""
    verbose = Mock()
    log_rotate_days = Mock()
    log_file = Mock()
    log_no_color = Mock()

    menuai = await bootstrap.async_setup_menuai(
        runner.RuntimeConfig(
            config_dir=get_test_config_dir(),
            verbose=verbose,
            log_rotate_days=log_rotate_days,
            log_file=log_file,
            log_no_color=log_no_color,
            skip_pip=True,
            recovery_mode=False,
        ),
    )

    assert "recovery_mode" in menuai.config.components
    assert menuai.config.config_dir == get_test_config_dir()
    assert menuai.config.skip_pip
    assert menuai.config.internal_url == "http://192.168.1.100:8123"
    assert menuai.config.external_url == "https://abcdef.ui.nabu.casa"


@pytest.mark.parametrize("load_registries", [False])
@patch("menuai.bootstrap.DEFAULT_INTEGRATIONS", set())
async def test_empty_integrations_list_is_only_sent_at_the_end_of_bootstrap(
    menuai: menuai,
) -> None:
    """Test empty integrations list is only sent at the end of bootstrap."""
    # setup times only tracked when not running
    menuai.set_state(CoreState.not_running)

    order = []

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            order.append(domain)
            await asyncio.sleep(0.05)

            async def _background_task():
                await asyncio.sleep(0.1)

            await menuai.async_create_task(_background_task())
            return True

        return async_setup

    mock_integration(
        menuai,
        MockModule(
            domain="normal_integration",
            async_setup=gen_domain_setup("normal_integration"),
            partial_manifest={"after_dependencies": ["an_after_dep"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="an_after_dep",
            async_setup=gen_domain_setup("an_after_dep"),
        ),
    )

    integrations = []

    @callback
    def _bootstrap_integrations(data):
        integrations.append(data)

    async_dispatcher_connect(
        menuai, SIGNAL_BOOTSTRAP_INTEGRATIONS, _bootstrap_integrations
    )
    with patch.object(bootstrap, "SLOW_STARTUP_CHECK_INTERVAL", 0.025):
        await bootstrap._async_set_up_integrations(
            menuai, {"normal_integration": {}, "an_after_dep": {}}
        )
        await menuai.async_block_till_done()

    assert integrations[0] != {}
    assert "an_after_dep" in integrations[0]
    assert integrations[-2] != {}
    assert integrations[-1] == {}

    assert "normal_integration" in menuai.config.components
    assert order == ["an_after_dep", "normal_integration"]


@pytest.mark.parametrize("load_registries", [False])
async def test_warning_logged_on_wrap_up_timeout(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test we log a warning on bootstrap timeout."""
    task: asyncio.Task | None = None

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            nonlocal task

            async def _not_marked_background_task():
                await asyncio.sleep(2)

            task = menuai.async_create_task(_not_marked_background_task())
            return True

        return async_setup

    mock_integration(
        menuai,
        MockModule(
            domain="normal_integration",
            async_setup=gen_domain_setup("normal_integration"),
            partial_manifest={},
        ),
    )

    with patch.object(bootstrap, "WRAP_UP_TIMEOUT", 0):
        await bootstrap._async_set_up_integrations(menuai, {"normal_integration": {}})

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    assert "Setup timed out for bootstrap" in caplog.text
    assert "waiting on" in caplog.text
    assert "_not_marked_background_task" in caplog.text


@pytest.mark.parametrize("load_registries", [False])
async def test_tasks_logged_that_block_stage_1(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test we log tasks that delay stage 1 startup."""

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            async def _not_marked_background_task():
                await asyncio.sleep(0.2)

            menuai.async_create_task(_not_marked_background_task())
            await asyncio.sleep(0.1)
            return True

        return async_setup

    mock_integration(
        menuai,
        MockModule(
            domain="normal_integration",
            async_setup=gen_domain_setup("normal_integration"),
            partial_manifest={},
        ),
    )

    original_stage_1 = bootstrap.STAGE_1_INTEGRATIONS
    with (
        patch.object(bootstrap, "STAGE_1_TIMEOUT", 0),
        patch.object(bootstrap, "COOLDOWN_TIME", 0),
        patch.object(
            bootstrap, "STAGE_1_INTEGRATIONS", {*original_stage_1, "normal_integration"}
        ),
    ):
        await bootstrap._async_set_up_integrations(menuai, {"normal_integration": {}})
        await menuai.async_block_till_done()

    assert "Setup timed out for stage 1 waiting on" in caplog.text
    assert "waiting on" in caplog.text
    assert "_not_marked_background_task" in caplog.text


@pytest.mark.parametrize("load_registries", [False])
async def test_tasks_logged_that_block_stage_2(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test we log tasks that delay stage 2 startup."""
    done_future = menuai.loop.create_future()

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            async def _not_marked_background_task():
                await done_future

            menuai.async_create_task(_not_marked_background_task())
            return True

        return async_setup

    mock_integration(
        menuai,
        MockModule(
            domain="normal_integration",
            async_setup=gen_domain_setup("normal_integration"),
            partial_manifest={},
        ),
    )

    wanted_messages = {
        "Setup timed out for stage 2 waiting on",
        "waiting on",
        "_not_marked_background_task",
    }

    def on_message_logged(log_record: logging.LogRecord, *args):
        for message in list(wanted_messages):
            if message in log_record.message:
                wanted_messages.remove(message)
        if not done_future.done() and not wanted_messages:
            done_future.set_result(None)
            return

    with (
        patch.object(bootstrap, "STAGE_2_TIMEOUT", 0),
        patch.object(bootstrap, "COOLDOWN_TIME", 0),
        patch.object(
            caplog.handler,
            "emit",
            wraps=caplog.handler.emit,
            side_effect=on_message_logged,
        ),
    ):
        await bootstrap._async_set_up_integrations(menuai, {"normal_integration": {}})
        async with asyncio.timeout(2):
            await done_future
        await menuai.async_block_till_done()

    assert not wanted_messages


@pytest.mark.parametrize("load_registries", [False])
async def test_bootstrap_is_cancellation_safe(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test cancellation during async_setup_component does not cancel bootstrap."""
    mock_integration(menuai, MockModule(domain="cancel_integration"))
    with patch.object(
        bootstrap, "async_setup_component", side_effect=asyncio.CancelledError
    ):
        await bootstrap._async_set_up_integrations(menuai, {"cancel_integration": {}})
        await menuai.async_block_till_done()

    assert "Error setting up integration cancel_integration" in caplog.text


@pytest.mark.parametrize("load_registries", [False])
async def test_bootstrap_empty_integrations(menuai: menuai) -> None:
    """Test setting up an empty integrations does not raise."""
    await bootstrap._async_setup_multi_components(menuai, set(), {})
    await menuai.async_block_till_done()


@pytest.mark.parametrize("load_registries", [False])
async def test_bootstrap_log_already_setup_stage(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test logging when all integrations in a stage were already setup."""
    with patch.object(bootstrap, "STAGE_1_INTEGRATIONS", {"frontend"}):
        await bootstrap._async_set_up_integrations(menuai, {})
        await menuai.async_block_till_done()

    assert "Already set up stage 1: {'frontend'}" in caplog.text


@pytest.fixture(name="mock_mqtt_config_flow")
def mock_mqtt_config_flow_fixture() -> Generator[None]:
    """Mock MQTT config flow."""

    class MockConfigFlow:
        """Mock the MQTT config flow."""

        VERSION = 1
        MINOR_VERSION = 1

    with mock_config_flow("mqtt", MockConfigFlow):
        yield


@pytest.mark.parametrize("integration", ["mqtt_eventstream", "mqtt_statestream"])
@pytest.mark.parametrize("load_registries", [False])
async def test_bootstrap_dependencies(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    integration: str,
    mock_mqtt_config_flow: None,
) -> None:
    """Test dependencies are set up correctly,."""
    entry = MockConfigEntry(domain="mqtt", data={"broker": "test-broker"})
    entry.add_to_menuai(menuai)

    calls: list[str] = []
    assertions: list[bool] = []

    async def async_mqtt_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
        """Assert the mqtt config entry was set up."""
        calls.append("mqtt")
        # assert the integration is not yet set up
        assertions.append(menuai.data["setup_done"][integration].done() is False)
        assertions.append(
            all(
                dependency in menuai.config.components
                for dependency in integrations[integration]["dependencies"]
            )
        )
        assertions.append(integration not in menuai.config.components)
        return True

    async def async_integration_setup(menuai: menuai, config: ConfigType) -> bool:
        """Assert the mqtt config entry was set up."""
        calls.append(integration)
        # assert mqtt was already set up
        assertions.append(
            "mqtt" not in menuai.data["setup_done"]
            or menuai.data["setup_done"]["mqtt"].done()
        )
        assertions.append("mqtt" in menuai.config.components)
        return True

    mqtt_integration = mock_integration(
        menuai,
        MockModule(
            "mqtt",
            async_setup_entry=async_mqtt_setup_entry,
            dependencies=["file_upload", "http"],
        ),
    )

    # We patch the _import platform method to avoid loading the platform module
    # to avoid depending on non core components in the tests.
    mqtt_integration._import_platform = Mock()
    mqtt_integration.platforms_exists = Mock(return_value=True)

    integrations = {
        "mqtt": {
            "dependencies": {"file_upload", "http"},
            "integration": mqtt_integration,
        },
        "mqtt_eventstream": {
            "dependencies": {"mqtt"},
            "integration": mock_integration(
                menuai,
                MockModule(
                    "mqtt_eventstream",
                    async_setup=async_integration_setup,
                    dependencies=["mqtt"],
                ),
            ),
        },
        "mqtt_statestream": {
            "dependencies": {"mqtt"},
            "integration": mock_integration(
                menuai,
                MockModule(
                    "mqtt_statestream",
                    async_setup=async_integration_setup,
                    dependencies=["mqtt"],
                ),
            ),
        },
        "file_upload": {
            "dependencies": {"http"},
            "integration": mock_integration(
                menuai,
                MockModule(
                    "file_upload",
                    dependencies=["http"],
                ),
            ),
        },
        "http": {
            "dependencies": set(),
            "integration": mock_integration(
                menuai,
                MockModule("http", dependencies=[]),
            ),
        },
    }

    async def mock_async_get_integrations(
        menuai: menuai, domains: Iterable[str]
    ) -> dict[str, Integration | Exception]:
        """Mock integrations."""
        return {domain: integrations[domain]["integration"] for domain in domains}

    with (
        patch(
            "menuai.setup.loader.async_get_integrations",
            side_effect=mock_async_get_integrations,
        ),
        patch(
            "menuai.config.async_process_component_config",
            return_value=config_util.IntegrationConfigInfo({}, []),
        ),
    ):
        bootstrap.async_set_domains_to_be_loaded(menuai, {integration})
        await bootstrap._async_setup_multi_components(menuai, {integration}, {})
        await menuai.async_block_till_done()

    for assertion in assertions:
        assert assertion

    assert calls == ["mqtt", integration]

    assert (
        f"Dependency {integration} will wait for dependencies dict_keys(['mqtt'])"
        in caplog.text
    )


@pytest.mark.parametrize("load_registries", [False])
async def test_bootstrap_dependency_not_found(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test setup when an integration has missing dependencies."""
    mock_integration(
        menuai,
        MockModule("good_integration", dependencies=[]),
    )
    # Simulate an integration with missing dependencies. While a core integration
    # can't have missing dependencies thanks to checks by menuaifest, there's no such
    # guarantee for custom integrations.
    mock_integration(
        menuai,
        MockModule("bad_integration", dependencies=["hahaha_crash_and_burn"]),
    )

    assert await bootstrap.async_from_config_dict(
        {"good_integration": {}, "bad_integration": {}}, menuai
    )

    assert "good_integration" in menuai.config.components
    assert "bad_integration" not in menuai.config.components

    assert "Unable to resolve dependencies for bad_integration" in caplog.text


async def test_pre_import_no_requirements(menuai: menuai) -> None:
    """Test pre-imported and do not have any requirements."""
    pre_imports = [
        name.removesuffix("_pre_import")
        for name in dir(bootstrap)
        if name.endswith("_pre_import")
    ]

    # Make sure future refactoring does not
    # accidentally remove the pre-imports
    # or change the naming convention without
    # updating this test.
    assert len(pre_imports) > 3

    for pre_import in pre_imports:
        integration = await loader.async_get_integration(menuai, pre_import)
        assert not integration.requirements


@pytest.mark.timeout(20)
async def test_bootstrap_does_not_preimport_stage_1_integrations() -> None:
    """Test that the bootstrap does not preimport stage 1 integrations.

    If this test fails it means that stage1 integrations are being
    imported too soon and will not get their requirements updated
    before they are loaded at runtime.
    """

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "import menuai.bootstrap; import sys; print(sys.modules)",
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    assert process.returncode == 0
    decoded_stdout = stdout.decode()

    # Ensure no stage1 integrations have been imported
    # as a side effect of importing the pre-imports
    for integration in bootstrap.STAGE_1_INTEGRATIONS:
        assert f"menuai.components.{integration}" not in decoded_stdout


@pytest.mark.parametrize("load_registries", [False])
@pytest.mark.usefixtures("enable_custom_integrations")
async def test_cancellation_does_not_leak_upward_from_async_setup(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test setting up an integration that raises asyncio.CancelledError."""
    await bootstrap._async_setup_multi_components(
        menuai, {"test_package_raises_cancelled_error"}, {}
    )
    await menuai.async_block_till_done()

    assert (
        "Error during setup of component test_package_raises_cancelled_error"
        in caplog.text
    )


@pytest.mark.parametrize("load_registries", [False])
@pytest.mark.usefixtures("enable_custom_integrations")
async def test_cancellation_does_not_leak_upward_from_async_setup_entry(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test setting up an integration that raises asyncio.CancelledError."""
    entry = MockConfigEntry(
        domain="test_package_raises_cancelled_error_config_entry", data={}
    )
    entry.add_to_menuai(menuai)
    await bootstrap._async_setup_multi_components(
        menuai, {"test_package_raises_cancelled_error_config_entry"}, {}
    )
    await menuai.async_block_till_done()

    await bootstrap._async_setup_multi_components(menuai, {"test_package"}, {})
    await menuai.async_block_till_done()
    assert (
        "Error setting up entry Mock Title for test_package_raises_cancelled_error_config_entry"
        in caplog.text
    )

    assert "test_package" in menuai.config.components
    assert "test_package_raises_cancelled_error_config_entry" in menuai.config.components


@pytest.mark.parametrize("load_registries", [False])
async def test_setup_does_base_platforms_first(menuai: menuai) -> None:
    """Test setup does base platforms first.

    Its important that base platforms are setup before other integrations
    in stage1/2 since they are the foundation for other integrations and
    almost every integration has to wait for them to be setup.
    """
    order = []

    def gen_domain_setup(domain):
        async def async_setup(menuai: menuai, config: ConfigType) -> bool:
            order.append(domain)
            return True

        return async_setup

    mock_integration(
        menuai, MockModule(domain="sensor", async_setup=gen_domain_setup("sensor"))
    )
    mock_integration(
        menuai,
        MockModule(
            domain="binary_sensor", async_setup=gen_domain_setup("binary_sensor")
        ),
    )
    mock_integration(
        menuai, MockModule(domain="root", async_setup=gen_domain_setup("root"))
    )
    mock_integration(
        menuai,
        MockModule(
            domain="first_dep",
            async_setup=gen_domain_setup("first_dep"),
            partial_manifest={"after_dependencies": ["root"]},
        ),
    )
    mock_integration(
        menuai,
        MockModule(
            domain="second_dep",
            async_setup=gen_domain_setup("second_dep"),
            partial_manifest={"after_dependencies": ["first_dep"]},
        ),
    )

    with patch(
        "menuai.components.logger.async_setup", gen_domain_setup("logger")
    ):
        await bootstrap._async_set_up_integrations(
            menuai,
            {
                "root": {},
                "first_dep": {},
                "second_dep": {},
                "sensor": {},
                "logger": {},
                "binary_sensor": {},
            },
        )

    assert "binary_sensor" in menuai.config.components
    assert "sensor" in menuai.config.components
    assert "root" in menuai.config.components
    assert "first_dep" in menuai.config.components
    assert "second_dep" in menuai.config.components

    assert order[0] == "logger"
    # base platforms (sensor/binary_sensor) should be setup before other integrations
    # but after logger integrations. The order of base platforms is not guaranteed,
    # only that they are setup before other integrations.
    assert set(order[1:3]) == {"sensor", "binary_sensor"}
    assert order[3:] == ["root", "first_dep", "second_dep"]


def test_should_rollover_is_always_false() -> None:
    """Test that shouldRollover always returns False."""
    assert (
        bootstrap._RotatingFileHandlerWithoutShouldRollOver(
            "any.log", delay=True
        ).shouldRollover(Mock())
        is False
    )


async def test_no_base_platforms_loaded_before_recorder(menuai: menuai) -> None:
    """Verify stage 0 not load base platforms before recorder.

    If a stage 0 integration implements base platforms or has a base
    platform in its dependencies and it loads before the recorder,
    because of platform-based YAML schema, it may inadvertently
    load integrations that expect the recorder to already be loaded.
    We need to ensure that doesn't happen.
    """
    IGNORE_BASE_PLATFORM_FILES = {
        # config/scene.py is not a platform
        "config": {"scene.py"},
        # websocket_api/sensor.py is using the platform YAML schema
        # we must not migrate it to an integration key until
        # we remove the platform YAML schema support for sensors
        "websocket_api": {"sensor.py"},
    }
    # person is a special case because it is a base platform
    # in the sense that it creates entities in its namespace
    # but its not used by other integrations to create entities
    # so we want to make sure it is not loaded before the recorder
    base_platforms = BASE_PLATFORMS | {"person"}

    integrations_before_recorder: set[str] = set()
    for _, integrations, _ in bootstrap.STAGE_0_INTEGRATIONS:
        integrations_before_recorder |= integrations
        if "recorder" in integrations:
            break
    else:
        pytest.fail("recorder not in stage 0")

    integrations_or_excs = await loader.async_get_integrations(
        menuai, integrations_before_recorder
    )
    integrations: dict[str, Integration] = {}
    for domain, integration in integrations_or_excs.items():
        assert not isinstance(integrations_or_excs, Exception)
        integrations[domain] = integration

    integrations_all_dependencies = (
        await loader.resolve_integrations_after_dependencies(
            menuai, integrations.values(), ignore_exceptions=True
        )
    )
    all_integrations = integrations.copy()
    all_integrations.update(
        (domain, loader.async_get_loaded_integration(menuai, domain))
        for domains in integrations_all_dependencies.values()
        for domain in domains
    )

    problems: dict[str, set[str]] = {}
    for domain in integrations:
        domain_with_base_platforms_deps = (
            integrations_all_dependencies[domain] & base_platforms
        )
        if domain_with_base_platforms_deps:
            problems[domain] = domain_with_base_platforms_deps
    assert not problems, (
        f"Integrations that are setup before recorder have base platforms in their dependencies: {problems}"
    )

    base_platform_py_files = {f"{base_platform}.py" for base_platform in base_platforms}

    for domain, integration in all_integrations.items():
        integration_base_platforms_files = (
            integration._top_level_files & base_platform_py_files
        )
        if ignore := IGNORE_BASE_PLATFORM_FILES.get(domain):
            integration_base_platforms_files -= ignore
        if integration_base_platforms_files:
            problems[domain] = integration_base_platforms_files
    assert not problems, (
        f"Integrations that are setup before recorder implement base platforms: {problems}"
    )


async def test_recorder_not_promoted(menuai: menuai) -> None:
    """Verify that recorder is not promoted to earlier than its own stage."""
    integrations_before_recorder: set[str] = set()
    for _, integrations, _ in bootstrap.STAGE_0_INTEGRATIONS:
        if "recorder" in integrations:
            break
        integrations_before_recorder |= integrations
    else:
        pytest.fail("recorder not in stage 0")

    integrations_or_excs = await loader.async_get_integrations(
        menuai, integrations_before_recorder
    )
    integrations: dict[str, Integration] = {}
    for domain, integration in integrations_or_excs.items():
        assert not isinstance(integrations_or_excs, Exception)
        integrations[domain] = integration

    integrations_all_dependencies = (
        await loader.resolve_integrations_after_dependencies(
            menuai, integrations.values(), ignore_exceptions=True
        )
    )
    all_integrations = integrations.copy()
    all_integrations.update(
        (domain, loader.async_get_loaded_integration(menuai, domain))
        for domains in integrations_all_dependencies.values()
        for domain in domains
    )

    assert "recorder" not in all_integrations
