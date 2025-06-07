"""Test the myUplink config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.myuplink.const import (
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import config_entry_oauth2_flow

from .const import CLIENT_ID, UNIQUE_ID

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

REDIRECT_URL = "https://example.com/auth/external/callback"
CURRENT_SCOPE = "WRITESYSTEM READSYSTEM offline_access"


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    access_token: str,
    setup_credentials,
) -> None:
    """Check full flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": REDIRECT_URL,
        },
    )

    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URL}"
        f"&state={state}"
        f"&scope={CURRENT_SCOPE.replace(' ', '+')}"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": access_token,
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch(
        f"menuai.components.{DOMAIN}.async_setup_entry", return_value=True
    ) as mock_setup:
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done()

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1

    assert result["data"]["auth_implementation"] == DOMAIN
    assert result["data"]["token"]["refresh_token"] == "mock-refresh-token"
    assert result["result"].unique_id == UNIQUE_ID


@pytest.mark.usefixtures("current_request_with_host")
@pytest.mark.parametrize(
    ("unique_id", "scope", "expected_reason"),
    [
        (
            UNIQUE_ID,
            CURRENT_SCOPE,
            "reauth_successful",
        ),
        (
            "wrong_uid",
            CURRENT_SCOPE,
            "account_mismatch",
        ),
        (
            UNIQUE_ID,
            "READSYSTEM offline_access",
            "reauth_successful",
        ),
    ],
    ids=["reauth_only", "account_mismatch", "wrong_scope"],
)
async def test_flow_reauth_abort(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    setup_credentials: None,
    mock_config_entry: MockConfigEntry,
    access_token: str,
    expires_at: float,
    unique_id: str,
    scope: str,
    expected_reason: str,
) -> None:
    """Test reauth step with correct params and mismatches."""

    CURRENT_TOKEN = {
        "auth_implementation": DOMAIN,
        "token": {
            "access_token": access_token,
            "scope": scope,
            "expires_in": 86399,
            "refresh_token": "3012bc9f-7a65-4240-b817-9154ffdcc30f",
            "token_type": "Bearer",
            "expires_at": expires_at,
        },
    }
    assert menuai.config_entries.async_update_entry(
        mock_config_entry, data=CURRENT_TOKEN, unique_id=unique_id
    )
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1

    result = await mock_config_entry.start_reauth_flow(menuai)

    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["step_id"] == "auth"

    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": REDIRECT_URL,
        },
    )
    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URL}"
        f"&state={state}"
        f"&scope={CURRENT_SCOPE.replace(' ', '+')}"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "updated-refresh-token",
            "access_token": access_token,
            "type": "Bearer",
            "expires_in": "60",
            "scope": CURRENT_SCOPE,
        },
    )

    with patch(
        f"menuai.components.{DOMAIN}.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done()

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == expected_reason

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1


@pytest.mark.usefixtures("current_request_with_host")
@pytest.mark.parametrize(
    ("unique_id", "scope", "expected_reason"),
    [
        (
            UNIQUE_ID,
            CURRENT_SCOPE,
            "reconfigure_successful",
        ),
        (
            "wrong_uid",
            CURRENT_SCOPE,
            "account_mismatch",
        ),
    ],
    ids=["reauth_only", "account_mismatch"],
)
async def test_flow_reconfigure_abort(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    setup_credentials: None,
    mock_config_entry: MockConfigEntry,
    access_token: str,
    expires_at: float,
    unique_id: str,
    scope: str,
    expected_reason: str,
) -> None:
    """Test reauth step with correct params and mismatches."""

    CURRENT_TOKEN = {
        "auth_implementation": DOMAIN,
        "token": {
            "access_token": access_token,
            "scope": scope,
            "expires_in": 86399,
            "refresh_token": "3012bc9f-7a65-4240-b817-9154ffdcc30f",
            "token_type": "Bearer",
            "expires_at": expires_at,
        },
    }
    assert menuai.config_entries.async_update_entry(
        mock_config_entry, data=CURRENT_TOKEN, unique_id=unique_id
    )
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1

    result = await mock_config_entry.start_reconfigure_flow(menuai)

    assert result["step_id"] == "auth"

    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": REDIRECT_URL,
        },
    )
    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URL}"
        f"&state={state}"
        f"&scope={CURRENT_SCOPE.replace(' ', '+')}"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "updated-refresh-token",
            "access_token": access_token,
            "type": "Bearer",
            "expires_in": "60",
            "scope": CURRENT_SCOPE,
        },
    )

    with patch(
        f"menuai.components.{DOMAIN}.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
        await menuai.async_block_till_done()

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == expected_reason

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
