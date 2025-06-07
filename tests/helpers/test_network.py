"""Test network helper."""

from unittest.mock import Mock, patch

from aiohttp import hdrs
from multidict import CIMultiDict, CIMultiDictProxy
import pytest
from yarl import URL

from menuai.components import cloud
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.helpers.network import (
    NoURLAvailableError,
    _get_cloud_url,
    _get_external_url,
    _get_internal_url,
    _get_request_host,
    get_supervisor_network_url,
    get_url,
    is_menuai_url,
    is_internal_request,
)

from tests.common import mock_component


@pytest.fixture(name="mock_current_request")
def mock_current_request_mock():
    """Mock the current request."""
    mock_current_request = Mock(name="mock_request")
    with patch(
        "menuai.helpers.network.http.current_request",
        Mock(get=mock_current_request),
    ):
        yield mock_current_request


async def test_get_url_internal(menuai: menuai) -> None:
    """Test getting an instance URL when the user has set an internal URL."""
    assert menuai.config.internal_url is None

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_current_request=True)

    # Test with internal URL: http://example.local:8123
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:8123"},
    )

    assert menuai.config.internal_url == "http://example.local:8123"
    assert _get_internal_url(menuai) == "http://example.local:8123"
    assert _get_internal_url(menuai, allow_ip=False) == "http://example.local:8123"

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_standard_port=True)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_ssl=True)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_current_request=True)

    with patch(
        "menuai.helpers.network._get_request_host", return_value="example.local"
    ):
        assert (
            _get_internal_url(menuai, require_current_request=True)
            == "http://example.local:8123"
        )

        with pytest.raises(NoURLAvailableError):
            _get_internal_url(
                menuai, require_current_request=True, require_standard_port=True
            )

        with pytest.raises(NoURLAvailableError):
            _get_internal_url(menuai, require_current_request=True, require_ssl=True)

    with (
        patch(
            "menuai.helpers.network._get_request_host",
            return_value="no_match.example.local",
        ),
        pytest.raises(NoURLAvailableError),
    ):
        _get_internal_url(menuai, require_current_request=True)

    # Test with internal URL: https://example.local:8123
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "https://example.local:8123"},
    )

    assert menuai.config.internal_url == "https://example.local:8123"
    assert _get_internal_url(menuai) == "https://example.local:8123"
    assert _get_internal_url(menuai, allow_ip=False) == "https://example.local:8123"
    assert _get_internal_url(menuai, require_ssl=True) == "https://example.local:8123"

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_standard_port=True)

    # Test with internal URL: http://example.local:80/
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:80/"},
    )

    assert menuai.config.internal_url == "http://example.local:80/"
    assert _get_internal_url(menuai) == "http://example.local"
    assert _get_internal_url(menuai, allow_ip=False) == "http://example.local"
    assert _get_internal_url(menuai, require_standard_port=True) == "http://example.local"

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_ssl=True)

    # Test with internal URL: https://example.local:443
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "https://example.local:443"},
    )

    assert menuai.config.internal_url == "https://example.local:443"
    assert _get_internal_url(menuai) == "https://example.local"
    assert _get_internal_url(menuai, allow_ip=False) == "https://example.local"
    assert (
        _get_internal_url(menuai, require_standard_port=True) == "https://example.local"
    )
    assert _get_internal_url(menuai, require_ssl=True) == "https://example.local"

    # Test with internal URL: https://192.168.0.1
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "https://192.168.0.1"},
    )

    assert menuai.config.internal_url == "https://192.168.0.1"
    assert _get_internal_url(menuai) == "https://192.168.0.1"
    assert _get_internal_url(menuai, require_standard_port=True) == "https://192.168.0.1"
    assert _get_internal_url(menuai, require_ssl=True) == "https://192.168.0.1"

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, allow_ip=False)

    # Test with internal URL: http://192.168.0.1:8123
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://192.168.0.1:8123"},
    )

    assert menuai.config.internal_url == "http://192.168.0.1:8123"
    assert _get_internal_url(menuai) == "http://192.168.0.1:8123"

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_standard_port=True)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_ssl=True)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, allow_ip=False)

    with patch(
        "menuai.helpers.network._get_request_host", return_value="192.168.0.1"
    ):
        assert (
            _get_internal_url(menuai, require_current_request=True)
            == "http://192.168.0.1:8123"
        )

        with pytest.raises(NoURLAvailableError):
            _get_internal_url(menuai, require_current_request=True, allow_ip=False)

        with pytest.raises(NoURLAvailableError):
            _get_internal_url(
                menuai, require_current_request=True, require_standard_port=True
            )

        with pytest.raises(NoURLAvailableError):
            _get_internal_url(menuai, require_current_request=True, require_ssl=True)


async def test_get_url_internal_fallback(menuai: menuai) -> None:
    """Test getting an instance URL when the user has not set an internal URL."""
    assert menuai.config.internal_url is None

    menuai.config.api = Mock(use_ssl=False, port=8123, local_ip="192.168.123.123")
    assert _get_internal_url(menuai) == "http://192.168.123.123:8123"

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, allow_ip=False)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_standard_port=True)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_ssl=True)

    menuai.config.api = Mock(use_ssl=False, port=80, local_ip="192.168.123.123")
    assert _get_internal_url(menuai) == "http://192.168.123.123"
    assert (
        _get_internal_url(menuai, require_standard_port=True) == "http://192.168.123.123"
    )

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, allow_ip=False)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_ssl=True)

    menuai.config.api = Mock(use_ssl=True, port=443)
    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_standard_port=True)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, allow_ip=False)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_ssl=True)

    # Do no accept any local loopback address as fallback
    menuai.config.api = Mock(use_ssl=False, port=80, local_ip="127.0.0.1")
    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_standard_port=True)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, allow_ip=False)

    with pytest.raises(NoURLAvailableError):
        _get_internal_url(menuai, require_ssl=True)


async def test_get_url_external(menuai: menuai) -> None:
    """Test getting an instance URL when the user has set an external URL."""
    assert menuai.config.external_url is None

    with pytest.raises(NoURLAvailableError):
        _get_external_url(menuai, require_current_request=True)

    # Test with external URL: http://example.com:8123
    await async_process_ha_core_config(
        menuai,
        {"external_url": "http://example.com:8123"},
    )

    assert menuai.config.external_url == "http://example.com:8123"
    assert _get_external_url(menuai) == "http://example.com:8123"
    assert _get_external_url(menuai, allow_cloud=False) == "http://example.com:8123"
    assert _get_external_url(menuai, allow_ip=False) == "http://example.com:8123"
    assert _get_external_url(menuai, prefer_cloud=True) == "http://example.com:8123"

    with pytest.raises(NoURLAvailableError):
        _get_external_url(menuai, require_standard_port=True)

    with pytest.raises(NoURLAvailableError):
        _get_external_url(menuai, require_ssl=True)

    with pytest.raises(NoURLAvailableError):
        _get_external_url(menuai, require_current_request=True)

    with patch(
        "menuai.helpers.network._get_request_host", return_value="example.com"
    ):
        assert (
            _get_external_url(menuai, require_current_request=True)
            == "http://example.com:8123"
        )

        with pytest.raises(NoURLAvailableError):
            _get_external_url(
                menuai, require_current_request=True, require_standard_port=True
            )

        with pytest.raises(NoURLAvailableError):
            _get_external_url(menuai, require_current_request=True, require_ssl=True)

    with (
        patch(
            "menuai.helpers.network._get_request_host",
            return_value="no_match.example.com",
        ),
        pytest.raises(NoURLAvailableError),
    ):
        _get_external_url(menuai, require_current_request=True)

    # Test with external URL: http://example.com:80/
    await async_process_ha_core_config(
        menuai,
        {"external_url": "http://example.com:80/"},
    )

    assert menuai.config.external_url == "http://example.com:80/"
    assert _get_external_url(menuai) == "http://example.com"
    assert _get_external_url(menuai, allow_cloud=False) == "http://example.com"
    assert _get_external_url(menuai, allow_ip=False) == "http://example.com"
    assert _get_external_url(menuai, prefer_cloud=True) == "http://example.com"
    assert _get_external_url(menuai, require_standard_port=True) == "http://example.com"

    with pytest.raises(NoURLAvailableError):
        _get_external_url(menuai, require_ssl=True)

    # Test with external url: https://example.com:443/
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com:443/"},
    )
    assert menuai.config.external_url == "https://example.com:443/"
    assert _get_external_url(menuai) == "https://example.com"
    assert _get_external_url(menuai, allow_cloud=False) == "https://example.com"
    assert _get_external_url(menuai, allow_ip=False) == "https://example.com"
    assert _get_external_url(menuai, prefer_cloud=True) == "https://example.com"
    assert _get_external_url(menuai, require_ssl=False) == "https://example.com"
    assert _get_external_url(menuai, require_standard_port=True) == "https://example.com"

    # Test with external URL: https://example.com:80
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com:80"},
    )
    assert menuai.config.external_url == "https://example.com:80"
    assert _get_external_url(menuai) == "https://example.com:80"
    assert _get_external_url(menuai, allow_cloud=False) == "https://example.com:80"
    assert _get_external_url(menuai, allow_ip=False) == "https://example.com:80"
    assert _get_external_url(menuai, prefer_cloud=True) == "https://example.com:80"
    assert _get_external_url(menuai, require_ssl=True) == "https://example.com:80"

    with pytest.raises(NoURLAvailableError):
        _get_external_url(menuai, require_standard_port=True)

    # Test with external URL: https://192.168.0.1
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://192.168.0.1"},
    )
    assert menuai.config.external_url == "https://192.168.0.1"
    assert _get_external_url(menuai) == "https://192.168.0.1"
    assert _get_external_url(menuai, allow_cloud=False) == "https://192.168.0.1"
    assert _get_external_url(menuai, prefer_cloud=True) == "https://192.168.0.1"
    assert _get_external_url(menuai, require_standard_port=True) == "https://192.168.0.1"

    with pytest.raises(NoURLAvailableError):
        _get_external_url(menuai, allow_ip=False)

    with pytest.raises(NoURLAvailableError):
        _get_external_url(menuai, require_ssl=True)

    with patch(
        "menuai.helpers.network._get_request_host", return_value="192.168.0.1"
    ):
        assert (
            _get_external_url(menuai, require_current_request=True)
            == "https://192.168.0.1"
        )

        with pytest.raises(NoURLAvailableError):
            _get_external_url(menuai, require_current_request=True, allow_ip=False)

        with pytest.raises(NoURLAvailableError):
            _get_external_url(menuai, require_current_request=True, require_ssl=True)

    with pytest.raises(NoURLAvailableError):
        _get_external_url(menuai, require_cloud=True)

    with patch(
        "menuai.components.cloud.async_remote_ui_url",
        return_value="https://example.nabu.casa",
    ):
        menuai.config.components.add("cloud")
        assert (
            _get_external_url(menuai, require_cloud=True) == "https://example.nabu.casa"
        )


async def test_get_cloud_url(menuai: menuai) -> None:
    """Test getting an instance URL when the user has set an external URL."""
    assert menuai.config.external_url is None
    menuai.config.components.add("cloud")

    with patch(
        "menuai.components.cloud.async_remote_ui_url",
        return_value="https://example.nabu.casa",
    ):
        assert _get_cloud_url(menuai) == "https://example.nabu.casa"

        with pytest.raises(NoURLAvailableError):
            _get_cloud_url(menuai, require_current_request=True)

        with patch(
            "menuai.helpers.network._get_request_host",
            return_value="example.nabu.casa",
        ):
            assert (
                _get_cloud_url(menuai, require_current_request=True)
                == "https://example.nabu.casa"
            )

        with (
            patch(
                "menuai.helpers.network._get_request_host",
                return_value="no_match.nabu.casa",
            ),
            pytest.raises(NoURLAvailableError),
        ):
            _get_cloud_url(menuai, require_current_request=True)

    with (
        patch(
            "menuai.components.cloud.async_remote_ui_url",
            side_effect=cloud.CloudNotAvailable,
        ),
        pytest.raises(NoURLAvailableError),
    ):
        _get_cloud_url(menuai)


async def test_get_external_url_cloud_fallback(menuai: menuai) -> None:
    """Test getting an external instance URL with cloud fallback."""
    assert menuai.config.external_url is None

    # Test with external URL: http://1.1.1.1:8123
    await async_process_ha_core_config(
        menuai,
        {"external_url": "http://1.1.1.1:8123"},
    )

    assert menuai.config.external_url == "http://1.1.1.1:8123"
    assert _get_external_url(menuai, prefer_cloud=True) == "http://1.1.1.1:8123"

    # Add Cloud to the previous test
    menuai.config.components.add("cloud")
    with patch(
        "menuai.components.cloud.async_remote_ui_url",
        return_value="https://example.nabu.casa",
    ):
        assert _get_external_url(menuai, allow_cloud=False) == "http://1.1.1.1:8123"
        assert _get_external_url(menuai, allow_ip=False) == "https://example.nabu.casa"
        assert _get_external_url(menuai, prefer_cloud=False) == "http://1.1.1.1:8123"
        assert _get_external_url(menuai, prefer_cloud=True) == "https://example.nabu.casa"
        assert _get_external_url(menuai, require_ssl=True) == "https://example.nabu.casa"
        assert (
            _get_external_url(menuai, require_standard_port=True)
            == "https://example.nabu.casa"
        )

    # Test with external URL: https://example.com
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com"},
    )

    assert menuai.config.external_url == "https://example.com"
    assert _get_external_url(menuai, prefer_cloud=True) == "https://example.com"

    # Add Cloud to the previous test
    menuai.config.components.add("cloud")
    with patch(
        "menuai.components.cloud.async_remote_ui_url",
        return_value="https://example.nabu.casa",
    ):
        assert _get_external_url(menuai, allow_cloud=False) == "https://example.com"
        assert _get_external_url(menuai, allow_ip=False) == "https://example.com"
        assert _get_external_url(menuai, prefer_cloud=False) == "https://example.com"
        assert _get_external_url(menuai, prefer_cloud=True) == "https://example.nabu.casa"
        assert _get_external_url(menuai, require_ssl=True) == "https://example.com"
        assert (
            _get_external_url(menuai, require_standard_port=True) == "https://example.com"
        )
        assert (
            _get_external_url(menuai, prefer_cloud=True, allow_cloud=False)
            == "https://example.com"
        )


async def test_get_url(menuai: menuai) -> None:
    """Test getting an instance URL."""
    assert menuai.config.external_url is None
    assert menuai.config.internal_url is None

    with pytest.raises(NoURLAvailableError):
        get_url(menuai)

    menuai.config.api = Mock(use_ssl=False, port=8123, local_ip="192.168.123.123")
    assert get_url(menuai) == "http://192.168.123.123:8123"
    assert get_url(menuai, prefer_external=True) == "http://192.168.123.123:8123"

    with pytest.raises(NoURLAvailableError):
        get_url(menuai, allow_internal=False)

    # Test only external
    menuai.config.api = None
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com"},
    )
    assert menuai.config.external_url == "https://example.com"
    assert menuai.config.internal_url is None
    assert get_url(menuai) == "https://example.com"

    # Test preference or allowance
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local", "external_url": "https://example.com"},
    )
    assert menuai.config.external_url == "https://example.com"
    assert menuai.config.internal_url == "http://example.local"
    assert get_url(menuai) == "http://example.local"
    assert get_url(menuai, prefer_external=True) == "https://example.com"
    assert get_url(menuai, allow_internal=False) == "https://example.com"
    assert (
        get_url(menuai, prefer_external=True, allow_external=False)
        == "http://example.local"
    )
    # Prefer external defaults to True if use_ssl=True
    menuai.config.api = Mock(use_ssl=True)
    assert get_url(menuai) == "https://example.com"
    menuai.config.api = Mock(use_ssl=False)
    assert get_url(menuai) == "http://example.local"
    menuai.config.api = None

    with pytest.raises(NoURLAvailableError):
        get_url(menuai, allow_external=False, require_ssl=True)

    with pytest.raises(NoURLAvailableError):
        get_url(menuai, allow_external=False, allow_internal=False)

    with pytest.raises(NoURLAvailableError):
        get_url(menuai, require_current_request=True)

    with (
        patch(
            "menuai.helpers.network._get_request_host",
            return_value="example.com",
        ),
        patch("menuai.helpers.http.current_request"),
    ):
        assert get_url(menuai, require_current_request=True) == "https://example.com"
        assert (
            get_url(menuai, require_current_request=True, require_ssl=True)
            == "https://example.com"
        )

        with pytest.raises(NoURLAvailableError):
            get_url(menuai, require_current_request=True, allow_external=False)

    with (
        patch(
            "menuai.helpers.network._get_request_host",
            return_value="example.local",
        ),
        patch("menuai.helpers.http.current_request"),
    ):
        assert get_url(menuai, require_current_request=True) == "http://example.local"

        with pytest.raises(NoURLAvailableError):
            get_url(menuai, require_current_request=True, allow_internal=False)

        with pytest.raises(NoURLAvailableError):
            get_url(menuai, require_current_request=True, require_ssl=True)

    with (
        patch(
            "menuai.helpers.network._get_request_host",
            return_value="no_match.example.com",
        ),
        pytest.raises(NoURLAvailableError),
    ):
        _get_internal_url(menuai, require_current_request=True)

    # Test allow_ip defaults when SSL specified
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://1.1.1.1"},
    )
    assert menuai.config.external_url == "https://1.1.1.1"
    assert get_url(menuai, allow_internal=False) == "https://1.1.1.1"
    menuai.config.api = Mock(use_ssl=False)
    assert get_url(menuai, allow_internal=False) == "https://1.1.1.1"
    menuai.config.api = Mock(use_ssl=True)
    with pytest.raises(NoURLAvailableError):
        assert get_url(menuai, allow_internal=False)


async def test_get_request_host_with_port(menuai: menuai) -> None:
    """Test getting the host of the current web request from the request context."""
    with pytest.raises(NoURLAvailableError):
        _get_request_host()

    with patch("menuai.helpers.http.current_request") as mock_request_context:
        mock_request = Mock()
        mock_request.headers = CIMultiDictProxy(
            CIMultiDict({hdrs.HOST: "example.com:8123"})
        )
        mock_request.url = URL("http://example.com:8123/test/request")
        mock_request.host = "example.com:8123"
        mock_request_context.get = Mock(return_value=mock_request)

        assert _get_request_host() == "example.com"


async def test_get_request_host_without_port(menuai: menuai) -> None:
    """Test getting the host of the current web request from the request context."""
    with pytest.raises(NoURLAvailableError):
        _get_request_host()

    with patch("menuai.helpers.http.current_request") as mock_request_context:
        mock_request = Mock()
        mock_request.headers = CIMultiDictProxy(CIMultiDict({hdrs.HOST: "example.com"}))
        mock_request.url = URL("http://example.com/test/request")
        mock_request.host = "example.com"
        mock_request_context.get = Mock(return_value=mock_request)

        assert _get_request_host() == "example.com"


async def test_get_request_ipv6_address(menuai: menuai) -> None:
    """Test getting the ipv6 host of the current web request from the request context."""
    with pytest.raises(NoURLAvailableError):
        _get_request_host()

    with patch("menuai.helpers.http.current_request") as mock_request_context:
        mock_request = Mock()
        mock_request.headers = CIMultiDictProxy(CIMultiDict({hdrs.HOST: "[::1]:8123"}))
        mock_request.url = URL("http://[::1]:8123/test/request")
        mock_request.host = "[::1]:8123"
        mock_request_context.get = Mock(return_value=mock_request)

        assert _get_request_host() == "::1"


async def test_get_request_ipv6_address_without_port(menuai: menuai) -> None:
    """Test getting the ipv6 host of the current web request from the request context."""
    with pytest.raises(NoURLAvailableError):
        _get_request_host()

    with patch("menuai.helpers.http.current_request") as mock_request_context:
        mock_request = Mock()
        mock_request.headers = CIMultiDictProxy(CIMultiDict({hdrs.HOST: "[::1]"}))
        mock_request.url = URL("http://[::1]/test/request")
        mock_request.host = "[::1]"
        mock_request_context.get = Mock(return_value=mock_request)

        assert _get_request_host() == "::1"


async def test_get_request_host_no_host_header(menuai: menuai) -> None:
    """Test getting the host of the current web request from the request context."""
    with pytest.raises(NoURLAvailableError):
        _get_request_host()

    with patch("menuai.helpers.http.current_request") as mock_request_context:
        mock_request = Mock()
        mock_request.headers = CIMultiDictProxy(CIMultiDict())
        mock_request.url = URL("/test/request")
        mock_request_context.get = Mock(return_value=mock_request)

        assert _get_request_host() is None


@patch("menuai.components.menuaiio.is_menuaiio", Mock(return_value=True))
@patch(
    "menuai.components.menuaiio.get_host_info",
    Mock(return_value={"hostname": "menuai"}),
)
async def test_get_current_request_url_with_known_host(
    menuai: menuai, current_request
) -> None:
    """Test getting current request URL with known hosts addresses."""
    menuai.config.api = Mock(use_ssl=False, port=8123, local_ip="127.0.0.1")
    assert menuai.config.internal_url is None

    with pytest.raises(NoURLAvailableError):
        get_url(menuai, require_current_request=True)

    # Ensure we accept localhost
    with patch(
        "menuai.helpers.network._get_request_host", return_value="localhost"
    ):
        assert get_url(menuai, require_current_request=True) == "http://localhost:8123"
        with pytest.raises(NoURLAvailableError):
            get_url(menuai, require_current_request=True, require_ssl=True)
        with pytest.raises(NoURLAvailableError):
            get_url(menuai, require_current_request=True, require_standard_port=True)

    # Ensure we accept local loopback ip (e.g., 127.0.0.1)
    with patch(
        "menuai.helpers.network._get_request_host", return_value="127.0.0.8"
    ):
        assert get_url(menuai, require_current_request=True) == "http://127.0.0.8:8123"
        with pytest.raises(NoURLAvailableError):
            get_url(menuai, require_current_request=True, allow_ip=False)

    # Ensure hostname from Supervisor is accepted transparently
    mock_component(menuai, "menuaiio")

    with patch(
        "menuai.helpers.network._get_request_host",
        return_value="menuai.local",
    ):
        assert (
            get_url(menuai, require_current_request=True)
            == "http://menuai.local:8123"
        )

    with patch(
        "menuai.helpers.network._get_request_host",
        return_value="menuai",
    ):
        assert (
            get_url(menuai, require_current_request=True) == "http://menuai:8123"
        )

    with (
        patch(
            "menuai.helpers.network._get_request_host",
            return_value="unknown.local",
        ),
        pytest.raises(NoURLAvailableError),
    ):
        get_url(menuai, require_current_request=True)


@patch(
    "menuai.helpers.network.is_menuaiio",
    Mock(return_value={"hostname": "menuai"}),
)
@patch(
    "menuai.components.menuaiio.get_host_info",
    Mock(return_value={"hostname": "hellohost"}),
)
async def test_is_internal_request(menuai: menuai, mock_current_request) -> None:
    """Test if accessing an instance on its internal URL."""
    # Test with internal URL: http://example.local:8123
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:8123"},
    )

    assert menuai.config.internal_url == "http://example.local:8123"

    # No request active
    mock_current_request.return_value = None
    assert not is_internal_request(menuai)

    mock_current_request.return_value = Mock(
        headers=CIMultiDictProxy(CIMultiDict({hdrs.HOST: "example.local:8123"})),
        host="example.local:8123",
        url=URL("http://example.local:8123"),
    )
    assert is_internal_request(menuai)

    mock_current_request.return_value = Mock(
        headers=CIMultiDictProxy(
            CIMultiDict({hdrs.HOST: "no_match.example.local:8123"})
        ),
        host="no_match.example.local:8123",
        url=URL("http://no_match.example.local:8123"),
    )
    assert not is_internal_request(menuai)

    # Test with internal URL: http://192.168.0.1:8123
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://192.168.0.1:8123"},
    )

    assert menuai.config.internal_url == "http://192.168.0.1:8123"
    assert not is_internal_request(menuai)

    mock_current_request.return_value = Mock(
        headers=CIMultiDictProxy(CIMultiDict({hdrs.HOST: "192.168.0.1:8123"})),
        host="192.168.0.1:8123",
        url=URL("http://192.168.0.1:8123"),
    )
    assert is_internal_request(menuai)

    # Test for matching against local IP
    menuai.config.api = Mock(use_ssl=False, local_ip="192.168.123.123", port=8123)
    for allowed in ("127.0.0.1", "192.168.123.123"):
        mock_current_request.return_value = Mock(
            headers=CIMultiDictProxy(CIMultiDict({hdrs.HOST: f"{allowed}:8123"})),
            host=f"{allowed}:8123",
            url=URL(f"http://{allowed}:8123"),
        )
        assert is_internal_request(menuai), mock_current_request.return_value.url

    # Test for matching against menuaiOS hostname
    for allowed in ("hellohost", "hellohost.local"):
        mock_current_request.return_value = Mock(
            headers=CIMultiDictProxy(CIMultiDict({hdrs.HOST: f"{allowed}:8123"})),
            host=f"{allowed}:8123",
            url=URL(f"http://{allowed}:8123"),
        )
        assert is_internal_request(menuai), mock_current_request.return_value.url


async def test_is_menuai_url(menuai: menuai) -> None:
    """Test is_menuai_url."""
    assert menuai.config.api is None
    assert menuai.config.internal_url is None
    assert menuai.config.external_url is None

    assert is_menuai_url(menuai, "http://example.com") is False
    assert is_menuai_url(menuai, "bad_url") is False
    assert is_menuai_url(menuai, "bad_url.com") is False
    assert is_menuai_url(menuai, "http:/bad_url.com") is False

    menuai.config.api = Mock(use_ssl=False, port=8123, local_ip="192.168.123.123")
    assert is_menuai_url(menuai, "http://192.168.123.123:8123") is True
    assert is_menuai_url(menuai, "https://192.168.123.123:8123") is False
    assert is_menuai_url(menuai, "http://192.168.123.123") is False

    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:8123"},
    )
    assert is_menuai_url(menuai, "http://example.local:8123") is True
    assert is_menuai_url(menuai, "https://example.local:8123") is False
    assert is_menuai_url(menuai, "http://example.local") is False

    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com:443"},
    )
    assert is_menuai_url(menuai, "https://example.com:443") is True
    assert is_menuai_url(menuai, "https://example.com") is True
    assert is_menuai_url(menuai, "http://example.com:443") is False
    assert is_menuai_url(menuai, "http://example.com") is False

    with patch(
        "menuai.components.cloud.async_remote_ui_url",
        return_value="https://example.nabu.casa",
    ):
        assert is_menuai_url(menuai, "https://example.nabu.casa") is False

        menuai.config.components.add("cloud")
        assert is_menuai_url(menuai, "https://example.nabu.casa:443") is True
        assert is_menuai_url(menuai, "https://example.nabu.casa") is True
        assert is_menuai_url(menuai, "http://example.nabu.casa:443") is False
        assert is_menuai_url(menuai, "http://example.nabu.casa") is False


async def test_is_menuai_url_addon_url(menuai: menuai) -> None:
    """Test is_menuai_url with a supervisor network URL."""
    assert is_menuai_url(menuai, "http://menuai:8123") is False

    menuai.config.api = Mock(use_ssl=False, port=8123, local_ip="192.168.123.123")
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:8123"},
    )
    assert is_menuai_url(menuai, "http://menuai:8123") is False

    mock_component(menuai, "menuaiio")
    assert is_menuai_url(menuai, "http://menuai:8123")
    assert not is_menuai_url(menuai, "https://menuai:8123")

    menuai.config.api = Mock(use_ssl=True, port=8123, local_ip="192.168.123.123")
    assert not is_menuai_url(menuai, "http://menuai:8123")
    assert is_menuai_url(menuai, "https://menuai:8123")


async def test_get_supervisor_network_url(menuai: menuai) -> None:
    """Test get_supervisor_network_url."""
    assert get_supervisor_network_url(menuai) is None

    menuai.config.api = Mock(use_ssl=False, port=8123, local_ip="192.168.123.123")
    await async_process_ha_core_config(menuai, {})
    assert get_supervisor_network_url(menuai) is None

    mock_component(menuai, "menuaiio")
    assert get_supervisor_network_url(menuai) == "http://menuai:8123"

    menuai.config.api = Mock(use_ssl=True, port=8123, local_ip="192.168.123.123")
    assert get_supervisor_network_url(menuai) is None
    assert (
        get_supervisor_network_url(menuai, allow_ssl=True) == "https://menuai:8123"
    )
