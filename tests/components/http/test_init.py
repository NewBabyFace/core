"""The tests for the MenuAI HTTP component."""

import asyncio
from collections.abc import Callable
from datetime import timedelta
from http import HTTPStatus
from ipaddress import ip_network
import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from menuai.auth.providers.menuai import menuaiAuthProvider
from menuai.components import cloud, http
from menuai.components.cloud import CloudNotAvailable
from menuai.core import menuai
from menuai.helpers import issue_registry as ir
from menuai.helpers.http import KEY_menuai
from menuai.helpers.network import NoURLAvailableError
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util
from menuai.util.ssl import server_context_intermediate, server_context_modern

from tests.common import async_call_logger_set_level, async_fire_time_changed
from tests.typing import ClientSessionGenerator


def _setup_broken_ssl_pem_files(tmp_path: Path) -> tuple[Path, Path]:
    test_dir = tmp_path / "test_broken_ssl"
    test_dir.mkdir()
    cert_path = test_dir / "cert.pem"
    cert_path.write_text("garbage")
    key_path = test_dir / "key.pem"
    key_path.write_text("garbage")
    return cert_path, key_path


def _setup_empty_ssl_pem_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    test_dir = tmp_path / "test_empty_ssl"
    test_dir.mkdir()
    cert_path = test_dir / "cert.pem"
    cert_path.write_text("-")
    peer_cert_path = test_dir / "peer_cert.pem"
    peer_cert_path.write_text("-")
    key_path = test_dir / "key.pem"
    key_path.write_text("-")
    return cert_path, key_path, peer_cert_path


@pytest.fixture
def mock_stack():
    """Mock extract stack."""
    with patch(
        "menuai.components.http.extract_stack",
        return_value=[
            Mock(
                filename="/home/paulus/core/menuai/core.py",
                lineno="23",
                line="do_something()",
            ),
            Mock(
                filename="/home/paulus/core/menuai/components/hue/light.py",
                lineno="23",
                line="self.light.is_on",
            ),
            Mock(
                filename="/home/paulus/core/menuai/components/http/__init__.py",
                lineno="157",
                line="base_url",
            ),
        ],
    ):
        yield


class TestView(http.menuaiView):
    """Test the HTTP views."""

    name = "test"
    url = "/hello"

    async def get(self, request):
        """Return a get request."""
        return "hello"


async def test_registering_view_while_running(
    menuai: menuai,
    aiohttp_client: ClientSessionGenerator,
    unused_tcp_port_factory: Callable[[], int],
) -> None:
    """Test that we can register a view while the server is running."""
    await async_setup_component(
        menuai,
        http.DOMAIN,
        {http.DOMAIN: {http.CONF_SERVER_PORT: unused_tcp_port_factory()}},
    )

    await menuai.async_start()
    # This raises a RuntimeError if app is frozen
    menuai.http.register_view(TestView)


async def test_menuai_assigned_to_app(menuai: menuai) -> None:
    """Test menuai instance is assigned to menuaiApp."""
    assert await async_setup_component(menuai, "api", {"http": {}})
    await menuai.async_start()
    assert menuai.http.app[KEY_menuai] == menuai
    assert menuai.http.app["menuai"] == menuai  # For backwards compatibility
    await menuai.async_stop()


async def test_not_log_password(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
    local_auth: menuaiAuthProvider,
) -> None:
    """Test access with password doesn't get logged."""
    assert await async_setup_component(menuai, "api", {"http": {}})
    client = await menuai_client_no_auth()
    logging.getLogger("aiohttp.access").setLevel(logging.INFO)

    resp = await client.get("/api/", params={"api_password": "test-password"})

    assert resp.status == HTTPStatus.UNAUTHORIZED
    logs = caplog.text

    # Ensure we don't log API passwords
    assert "/api/" in logs
    assert "some-pass" not in logs


async def test_proxy_config(menuai: menuai) -> None:
    """Test use_x_forwarded_for must config together with trusted_proxies."""
    assert (
        await async_setup_component(
            menuai,
            "http",
            {
                "http": {
                    http.CONF_USE_X_FORWARDED_FOR: True,
                    http.CONF_TRUSTED_PROXIES: ["127.0.0.1"],
                }
            },
        )
        is True
    )


async def test_proxy_config_only_use_xff(menuai: menuai) -> None:
    """Test use_x_forwarded_for must config together with trusted_proxies."""
    assert (
        await async_setup_component(
            menuai, "http", {"http": {http.CONF_USE_X_FORWARDED_FOR: True}}
        )
        is not True
    )


async def test_proxy_config_only_trust_proxies(menuai: menuai) -> None:
    """Test use_x_forwarded_for must config together with trusted_proxies."""
    assert (
        await async_setup_component(
            menuai, "http", {"http": {http.CONF_TRUSTED_PROXIES: ["127.0.0.1"]}}
        )
        is not True
    )


async def test_ssl_profile_defaults_modern(menuai: menuai, tmp_path: Path) -> None:
    """Test default ssl profile."""

    cert_path, key_path, _ = await menuai.async_add_executor_job(
        _setup_empty_ssl_pem_files, tmp_path
    )

    with (
        patch("ssl.SSLContext.load_cert_chain"),
        patch(
            "menuai.util.ssl.server_context_modern",
            side_effect=server_context_modern,
        ) as mock_context,
    ):
        assert (
            await async_setup_component(
                menuai,
                "http",
                {"http": {"ssl_certificate": cert_path, "ssl_key": key_path}},
            )
            is True
        )
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert len(mock_context.mock_calls) == 1


async def test_ssl_profile_change_intermediate(
    menuai: menuai, tmp_path: Path
) -> None:
    """Test setting ssl profile to intermediate."""

    cert_path, key_path, _ = await menuai.async_add_executor_job(
        _setup_empty_ssl_pem_files, tmp_path
    )

    with (
        patch("ssl.SSLContext.load_cert_chain"),
        patch(
            "menuai.util.ssl.server_context_intermediate",
            side_effect=server_context_intermediate,
        ) as mock_context,
    ):
        assert (
            await async_setup_component(
                menuai,
                "http",
                {
                    "http": {
                        "ssl_profile": "intermediate",
                        "ssl_certificate": cert_path,
                        "ssl_key": key_path,
                    }
                },
            )
            is True
        )
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert len(mock_context.mock_calls) == 1


async def test_ssl_profile_change_modern(menuai: menuai, tmp_path: Path) -> None:
    """Test setting ssl profile to modern."""

    cert_path, key_path, _ = await menuai.async_add_executor_job(
        _setup_empty_ssl_pem_files, tmp_path
    )

    with (
        patch("ssl.SSLContext.load_cert_chain"),
        patch(
            "menuai.util.ssl.server_context_modern",
            side_effect=server_context_modern,
        ) as mock_context,
    ):
        assert (
            await async_setup_component(
                menuai,
                "http",
                {
                    "http": {
                        "ssl_profile": "modern",
                        "ssl_certificate": cert_path,
                        "ssl_key": key_path,
                    }
                },
            )
            is True
        )
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert len(mock_context.mock_calls) == 1


async def test_peer_cert(menuai: menuai, tmp_path: Path) -> None:
    """Test required peer cert."""
    cert_path, key_path, peer_cert_path = await menuai.async_add_executor_job(
        _setup_empty_ssl_pem_files, tmp_path
    )

    with (
        patch("ssl.SSLContext.load_cert_chain"),
        patch("ssl.SSLContext.load_verify_locations") as mock_load_verify_locations,
        patch(
            "menuai.util.ssl.server_context_modern",
            side_effect=server_context_modern,
        ) as mock_context,
    ):
        assert (
            await async_setup_component(
                menuai,
                "http",
                {
                    "http": {
                        "ssl_peer_certificate": peer_cert_path,
                        "ssl_profile": "modern",
                        "ssl_certificate": cert_path,
                        "ssl_key": key_path,
                    }
                },
            )
            is True
        )
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert len(mock_context.mock_calls) == 1
    assert len(mock_load_verify_locations.mock_calls) == 1


async def test_emergency_ssl_certificate_when_invalid(
    menuai: menuai, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Test http can startup with an emergency self signed cert when the current one is broken."""

    cert_path, key_path = await menuai.async_add_executor_job(
        _setup_broken_ssl_pem_files, tmp_path
    )

    menuai.config.recovery_mode = True
    assert (
        await async_setup_component(
            menuai,
            "http",
            {
                "http": {"ssl_certificate": cert_path, "ssl_key": key_path},
            },
        )
        is True
    )

    await menuai.async_start()
    await menuai.async_block_till_done()
    assert (
        "MenuAI is running in recovery mode with an emergency self signed ssl certificate because the configured SSL certificate was not usable"
        in caplog.text
    )

    assert menuai.http.site is not None


async def test_emergency_ssl_certificate_not_used_when_not_recovery_mode(
    menuai: menuai, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Test an emergency cert is only used in recovery mode."""

    cert_path, key_path = await menuai.async_add_executor_job(
        _setup_broken_ssl_pem_files, tmp_path
    )

    assert (
        await async_setup_component(
            menuai, "http", {"http": {"ssl_certificate": cert_path, "ssl_key": key_path}}
        )
        is False
    )


async def test_emergency_ssl_certificate_when_invalid_get_url_fails(
    menuai: menuai, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Test http falls back to no ssl when an emergency cert cannot be created when the configured one is broken.

    Ensure we can still start of we cannot determine the external url as well.
    """
    cert_path, key_path = await menuai.async_add_executor_job(
        _setup_broken_ssl_pem_files, tmp_path
    )
    menuai.config.recovery_mode = True

    with patch(
        "menuai.components.http.get_url", side_effect=NoURLAvailableError
    ) as mock_get_url:
        assert (
            await async_setup_component(
                menuai,
                "http",
                {
                    "http": {"ssl_certificate": cert_path, "ssl_key": key_path},
                },
            )
            is True
        )
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert len(mock_get_url.mock_calls) == 1
    assert (
        "MenuAI is running in recovery mode with an emergency self signed ssl certificate because the configured SSL certificate was not usable"
        in caplog.text
    )

    assert menuai.http.site is not None


async def test_invalid_ssl_and_cannot_create_emergency_cert(
    menuai: menuai, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Test http falls back to no ssl when an emergency cert cannot be created when the configured one is broken."""

    cert_path, key_path = await menuai.async_add_executor_job(
        _setup_broken_ssl_pem_files, tmp_path
    )
    menuai.config.recovery_mode = True

    with patch(
        "menuai.components.http.x509.CertificateBuilder", side_effect=OSError
    ) as mock_builder:
        assert (
            await async_setup_component(
                menuai,
                "http",
                {
                    "http": {"ssl_certificate": cert_path, "ssl_key": key_path},
                },
            )
            is True
        )
        await menuai.async_start()
        await menuai.async_block_till_done()
    assert "Could not create an emergency self signed ssl certificate" in caplog.text
    assert len(mock_builder.mock_calls) == 1

    assert menuai.http.site is not None


async def test_invalid_ssl_and_cannot_create_emergency_cert_with_ssl_peer_cert(
    menuai: menuai, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Test http falls back to no ssl when an emergency cert cannot be created when the configured one is broken.

    When there is a peer cert verification and we cannot create
    an emergency cert (probably will never happen since this means
    the system is very broken), we do not want to startup http
    as it would allow connections that are not verified by the cert.
    """

    cert_path, key_path = await menuai.async_add_executor_job(
        _setup_broken_ssl_pem_files, tmp_path
    )
    menuai.config.recovery_mode = True

    with patch(
        "menuai.components.http.x509.CertificateBuilder", side_effect=OSError
    ) as mock_builder:
        assert (
            await async_setup_component(
                menuai,
                "http",
                {
                    "http": {
                        "ssl_certificate": cert_path,
                        "ssl_key": key_path,
                        "ssl_peer_certificate": cert_path,
                    },
                },
            )
            is False
        )
        await menuai.async_start()
        await menuai.async_block_till_done()
    assert "Could not create an emergency self signed ssl certificate" in caplog.text
    assert len(mock_builder.mock_calls) == 1


async def test_cors_defaults(menuai: menuai) -> None:
    """Test the CORS default settings."""
    with patch("menuai.components.http.setup_cors") as mock_setup:
        assert await async_setup_component(menuai, "http", {})

    assert len(mock_setup.mock_calls) == 1
    assert mock_setup.mock_calls[0][1][1] == ["https://cast.home-assistant.io"]


async def test_storing_config(
    menuai: menuai,
    aiohttp_client: ClientSessionGenerator,
    unused_tcp_port_factory: Callable[[], int],
) -> None:
    """Test that we store last working config."""
    config = {
        http.CONF_SERVER_PORT: unused_tcp_port_factory(),
        "use_x_forwarded_for": True,
        "trusted_proxies": ["192.168.1.100"],
    }

    assert await async_setup_component(menuai, http.DOMAIN, {http.DOMAIN: config})

    await menuai.async_start()

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=200))
    await menuai.async_block_till_done()

    restored = await http.async_get_last_config(menuai)
    restored["trusted_proxies"][0] = ip_network(restored["trusted_proxies"][0])

    assert restored == http.HTTP_SCHEMA(config)


async def test_logging(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Testing the access log works."""
    await asyncio.gather(
        *(
            async_setup_component(menuai, component, {})
            for component in ("http", "logger", "api")
        )
    )
    menuai.states.async_set("logging.entity", "hello")
    async with async_call_logger_set_level(
        "aiohttp.access", "INFO", menuai=menuai, caplog=caplog
    ):
        client = await menuai_client()
        response = await client.get("/api/states/logging.entity")
        assert response.status == HTTPStatus.OK

        assert "GET /api/states/logging.entity" in caplog.text
        caplog.clear()
    async with async_call_logger_set_level(
        "aiohttp.access", "WARNING", menuai=menuai, caplog=caplog
    ):
        response = await client.get("/api/states/logging.entity")
        assert response.status == HTTPStatus.OK
        assert "GET /api/states/logging.entity" not in caplog.text


async def test_register_static_paths(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test registering a static path with old api."""
    assert await async_setup_component(menuai, "frontend", {})
    path = str(Path(__file__).parent)
    menuai.http.register_static_path("/something", path)
    client = await menuai_client()
    resp = await client.get("/something/__init__.py")
    assert resp.status == HTTPStatus.OK

    assert (
        "Detected code that calls menuai.http.register_static_path "
        "which is deprecated because it does blocking I/O in the "
        "event loop, instead call "
        "`await menuai.http.async_register_static_paths"
    ) in caplog.text


async def test_ssl_issue_if_no_urls_configured(
    menuai: menuai,
    tmp_path: Path,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test raising SSL issue if no external or internal URL is configured."""

    assert menuai.config.external_url is None
    assert menuai.config.internal_url is None

    cert_path, key_path, _ = await menuai.async_add_executor_job(
        _setup_empty_ssl_pem_files, tmp_path
    )

    with (
        patch("ssl.SSLContext.load_cert_chain"),
        patch(
            "menuai.util.ssl.server_context_modern",
            side_effect=server_context_modern,
        ),
    ):
        assert await async_setup_component(
            menuai,
            "http",
            {"http": {"ssl_certificate": cert_path, "ssl_key": key_path}},
        )
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert ("http", "ssl_configured_without_configured_urls") in issue_registry.issues


async def test_ssl_issue_if_using_cloud(
    menuai: menuai,
    tmp_path: Path,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test raising no SSL issue if not right configured but using cloud."""
    assert menuai.config.external_url is None
    assert menuai.config.internal_url is None

    cert_path, key_path, _ = await menuai.async_add_executor_job(
        _setup_empty_ssl_pem_files, tmp_path
    )

    with (
        patch("ssl.SSLContext.load_cert_chain"),
        patch.object(cloud, "async_remote_ui_url", return_value="https://example.com"),
        patch(
            "menuai.util.ssl.server_context_modern",
            side_effect=server_context_modern,
        ),
    ):
        assert await async_setup_component(
            menuai,
            "http",
            {"http": {"ssl_certificate": cert_path, "ssl_key": key_path}},
        )
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert (
        "http",
        "ssl_configured_without_configured_urls",
    ) not in issue_registry.issues


async def test_ssl_issue_if_not_connected_to_cloud(
    menuai: menuai,
    tmp_path: Path,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test raising no SSL issue if not right configured and not connected to cloud."""
    assert menuai.config.external_url is None
    assert menuai.config.internal_url is None

    cert_path, key_path, _ = await menuai.async_add_executor_job(
        _setup_empty_ssl_pem_files, tmp_path
    )

    with (
        patch("ssl.SSLContext.load_cert_chain"),
        patch(
            "menuai.util.ssl.server_context_modern",
            side_effect=server_context_modern,
        ),
        patch(
            "menuai.components.cloud.async_remote_ui_url",
            side_effect=CloudNotAvailable,
        ),
    ):
        assert await async_setup_component(
            menuai,
            "http",
            {"http": {"ssl_certificate": cert_path, "ssl_key": key_path}},
        )
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert ("http", "ssl_configured_without_configured_urls") in issue_registry.issues


@pytest.mark.parametrize(
    ("external_url", "internal_url"),
    [
        ("https://example.com", "https://example.local"),
        (None, "http://example.local"),
        ("https://example.com", None),
    ],
)
async def test_ssl_issue_urls_configured(
    menuai: menuai,
    tmp_path: Path,
    issue_registry: ir.IssueRegistry,
    external_url: str | None,
    internal_url: str | None,
) -> None:
    """Test raising SSL issue if no external or internal URL is configured."""

    cert_path, key_path, _ = await menuai.async_add_executor_job(
        _setup_empty_ssl_pem_files, tmp_path
    )

    menuai.config.external_url = external_url
    menuai.config.internal_url = internal_url

    with (
        patch("ssl.SSLContext.load_cert_chain"),
        patch(
            "menuai.util.ssl.server_context_modern",
            side_effect=server_context_modern,
        ),
    ):
        assert await async_setup_component(
            menuai,
            "http",
            {"http": {"ssl_certificate": cert_path, "ssl_key": key_path}},
        )
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert (
        "http",
        "ssl_configured_without_configured_urls",
    ) not in issue_registry.issues
