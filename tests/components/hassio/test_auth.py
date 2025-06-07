"""The tests for the menuaiio component."""

from http import HTTPStatus
from unittest.mock import Mock, patch

from aiohttp.test_utils import TestClient

from menuai.auth.providers.menuai import InvalidAuth


async def test_auth_success(menuaiio_client_supervisor: TestClient) -> None:
    """Test no auth needed for ."""
    with patch(
        "menuai.auth.providers.menuai."
        "menuaiAuthProvider.async_validate_login",
    ) as mock_login:
        resp = await menuaiio_client_supervisor.post(
            "/api/menuaiio_auth",
            json={"username": "test", "password": "123456", "addon": "samba"},
        )

        # Check we got right response
        assert resp.status == HTTPStatus.OK
        mock_login.assert_called_with("test", "123456")


async def test_auth_fails_no_supervisor(menuaiio_client: TestClient) -> None:
    """Test if only supervisor can access."""
    with patch(
        "menuai.auth.providers.menuai."
        "menuaiAuthProvider.async_validate_login",
    ) as mock_login:
        resp = await menuaiio_client.post(
            "/api/menuaiio_auth",
            json={"username": "test", "password": "123456", "addon": "samba"},
        )

        # Check we got right response
        assert resp.status == HTTPStatus.UNAUTHORIZED
        assert not mock_login.called


async def test_auth_fails_no_auth(menuaiio_noauth_client: TestClient) -> None:
    """Test if only supervisor can access."""
    with patch(
        "menuai.auth.providers.menuai."
        "menuaiAuthProvider.async_validate_login",
    ) as mock_login:
        resp = await menuaiio_noauth_client.post(
            "/api/menuaiio_auth",
            json={"username": "test", "password": "123456", "addon": "samba"},
        )

        # Check we got right response
        assert resp.status == HTTPStatus.UNAUTHORIZED
        assert not mock_login.called


async def test_login_error(menuaiio_client_supervisor: TestClient) -> None:
    """Test no auth needed for error."""
    with patch(
        "menuai.auth.providers.menuai."
        "menuaiAuthProvider.async_validate_login",
        Mock(side_effect=InvalidAuth()),
    ) as mock_login:
        resp = await menuaiio_client_supervisor.post(
            "/api/menuaiio_auth",
            json={"username": "test", "password": "123456", "addon": "samba"},
        )

        # Check we got right response
        assert resp.status == HTTPStatus.NOT_FOUND
        mock_login.assert_called_with("test", "123456")


async def test_login_no_data(menuaiio_client_supervisor: TestClient) -> None:
    """Test auth with no data -> error."""
    with patch(
        "menuai.auth.providers.menuai."
        "menuaiAuthProvider.async_validate_login",
        Mock(side_effect=InvalidAuth()),
    ) as mock_login:
        resp = await menuaiio_client_supervisor.post("/api/menuaiio_auth")

        # Check we got right response
        assert resp.status == HTTPStatus.BAD_REQUEST
        assert not mock_login.called


async def test_login_no_username(menuaiio_client_supervisor: TestClient) -> None:
    """Test auth with no username in data -> error."""
    with patch(
        "menuai.auth.providers.menuai."
        "menuaiAuthProvider.async_validate_login",
        Mock(side_effect=InvalidAuth()),
    ) as mock_login:
        resp = await menuaiio_client_supervisor.post(
            "/api/menuaiio_auth", json={"password": "123456", "addon": "samba"}
        )

        # Check we got right response
        assert resp.status == HTTPStatus.BAD_REQUEST
        assert not mock_login.called


async def test_login_success_extra(menuaiio_client_supervisor: TestClient) -> None:
    """Test auth with extra data."""
    with patch(
        "menuai.auth.providers.menuai."
        "menuaiAuthProvider.async_validate_login",
    ) as mock_login:
        resp = await menuaiio_client_supervisor.post(
            "/api/menuaiio_auth",
            json={
                "username": "test",
                "password": "123456",
                "addon": "samba",
                "path": "/share",
            },
        )

        # Check we got right response
        assert resp.status == HTTPStatus.OK
        mock_login.assert_called_with("test", "123456")


async def test_password_success(menuaiio_client_supervisor: TestClient) -> None:
    """Test no auth needed for ."""
    with patch(
        "menuai.auth.providers.menuai."
        "menuaiAuthProvider.async_change_password",
    ) as mock_change:
        resp = await menuaiio_client_supervisor.post(
            "/api/menuaiio_auth/password_reset",
            json={"username": "test", "password": "123456"},
        )

        # Check we got right response
        assert resp.status == HTTPStatus.OK
        mock_change.assert_called_with("test", "123456")


async def test_password_fails_no_supervisor(menuaiio_client: TestClient) -> None:
    """Test if only supervisor can access."""
    resp = await menuaiio_client.post(
        "/api/menuaiio_auth/password_reset",
        json={"username": "test", "password": "123456"},
    )

    # Check we got right response
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_password_fails_no_auth(menuaiio_noauth_client: TestClient) -> None:
    """Test if only supervisor can access."""
    resp = await menuaiio_noauth_client.post(
        "/api/menuaiio_auth/password_reset",
        json={"username": "test", "password": "123456"},
    )

    # Check we got right response
    assert resp.status == HTTPStatus.UNAUTHORIZED


async def test_password_no_user(menuaiio_client_supervisor: TestClient) -> None:
    """Test changing password for invalid user."""
    resp = await menuaiio_client_supervisor.post(
        "/api/menuaiio_auth/password_reset",
        json={"username": "test", "password": "123456"},
    )

    # Check we got right response
    assert resp.status == HTTPStatus.NOT_FOUND
