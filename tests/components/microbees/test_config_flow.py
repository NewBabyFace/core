"""Tests for config flow."""

from unittest.mock import AsyncMock, patch

from microBeesPy import MicroBeesException
import pytest

from menuai.components.microbees.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import config_entry_oauth2_flow

from . import setup_integration
from .conftest import CLIENT_ID, MICROBEES_AUTH_URI, MICROBEES_TOKEN_URI, SCOPES

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    microbees: AsyncMock,
) -> None:
    """Check full flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )
    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"] == (
        f"{MICROBEES_AUTH_URI}?"
        f"response_type=code&client_id={CLIENT_ID}&"
        "redirect_uri=https://example.com/auth/external/callback&"
        f"state={state}"
        f"&scope={'+'.join(SCOPES)}"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"
    aioclient_mock.clear_requests()
    aioclient_mock.post(
        MICROBEES_TOKEN_URI,
        json={
            "access_token": "mock-access-token",
            "token_type": "bearer",
            "refresh_token": "mock-refresh-token",
            "expires_in": 99999,
            "scope": " ".join(SCOPES),
            "client_id": CLIENT_ID,
        },
    )

    with patch(
        "menuai.components.microbees.async_setup_entry", return_value=True
    ) as mock_setup:
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test@microbees.com"
    assert "result" in result
    assert result["result"].unique_id == 54321
    assert "token" in result["result"].data
    assert result["result"].data["token"]["access_token"] == "mock-access-token"
    assert result["result"].data["token"]["refresh_token"] == "mock-refresh-token"


@pytest.mark.usefixtures("current_request_with_host")
async def test_config_non_unique_profile(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    microbees: AsyncMock,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test setup a non-unique profile."""
    await setup_integration(menuai, config_entry)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )

    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"] == (
        f"{MICROBEES_AUTH_URI}?"
        f"response_type=code&client_id={CLIENT_ID}&"
        "redirect_uri=https://example.com/auth/external/callback&"
        f"state={state}"
        f"&scope={'+'.join(SCOPES)}"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        MICROBEES_TOKEN_URI,
        json={
            "access_token": "mock-access-token",
            "token_type": "bearer",
            "refresh_token": "mock-refresh-token",
            "expires_in": 99999,
            "scope": " ".join(SCOPES),
            "client_id": CLIENT_ID,
        },
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("current_request_with_host")
async def test_config_reauth_profile(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    microbees: AsyncMock,
) -> None:
    """Test reauth an existing profile reauthenticates the config entry."""
    await setup_integration(menuai, config_entry)

    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )
    assert result["url"] == (
        f"{MICROBEES_AUTH_URI}?"
        f"response_type=code&client_id={CLIENT_ID}&"
        "redirect_uri=https://example.com/auth/external/callback&"
        f"state={state}"
        f"&scope={'+'.join(SCOPES)}"
    )
    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        MICROBEES_TOKEN_URI,
        json={
            "access_token": "mock-access-token",
            "token_type": "bearer",
            "refresh_token": "mock-refresh-token",
            "expires_in": 99999,
            "scope": " ".join(SCOPES),
            "client_id": CLIENT_ID,
        },
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


@pytest.mark.usefixtures("current_request_with_host")
async def test_config_reauth_wrong_account(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    microbees: AsyncMock,
) -> None:
    """Test reauth with wrong account."""
    await setup_integration(menuai, config_entry)
    microbees.return_value.getMyProfile.return_value.id = 12345
    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )
    assert result["url"] == (
        f"{MICROBEES_AUTH_URI}?"
        f"response_type=code&client_id={CLIENT_ID}&"
        "redirect_uri=https://example.com/auth/external/callback&"
        f"state={state}"
        f"&scope={'+'.join(SCOPES)}"
    )
    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        MICROBEES_TOKEN_URI,
        json={
            "access_token": "mock-access-token",
            "token_type": "bearer",
            "refresh_token": "mock-refresh-token",
            "expires_in": 99999,
            "scope": " ".join(SCOPES),
            "client_id": CLIENT_ID,
        },
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"


@pytest.mark.usefixtures("current_request_with_host")
async def test_config_flow_with_invalid_credentials(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    microbees: AsyncMock,
) -> None:
    """Test flow with invalid credentials."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )

    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"] == (
        f"{MICROBEES_AUTH_URI}?"
        f"response_type=code&client_id={CLIENT_ID}&"
        "redirect_uri=https://example.com/auth/external/callback&"
        f"state={state}"
        f"&scope={'+'.join(SCOPES)}"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        MICROBEES_TOKEN_URI,
        json={
            "status": 401,
            "error": "Invalid Params: invalid client id/secret",
        },
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "oauth_error"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (MicroBeesException("Invalid auth"), "invalid_auth"),
        (Exception("Unexpected error"), "unknown"),
    ],
)
@pytest.mark.usefixtures("current_request_with_host")
async def test_unexpected_exceptions(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    microbees: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test unknown error from server."""
    await setup_integration(menuai, config_entry)
    microbees.return_value.getMyProfile.side_effect = exception

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )
    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"] == (
        f"{MICROBEES_AUTH_URI}?"
        f"response_type=code&client_id={CLIENT_ID}&"
        "redirect_uri=https://example.com/auth/external/callback&"
        f"state={state}"
        f"&scope={'+'.join(SCOPES)}"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"
    aioclient_mock.clear_requests()
    aioclient_mock.post(
        MICROBEES_TOKEN_URI,
        json={
            "access_token": "mock-access-token",
            "token_type": "bearer",
            "refresh_token": "mock-refresh-token",
            "expires_in": 99999,
            "scope": " ".join(SCOPES),
            "client_id": CLIENT_ID,
        },
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == error
