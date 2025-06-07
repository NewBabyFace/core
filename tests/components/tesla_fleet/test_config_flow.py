"""Test the Tesla Fleet config flow."""

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from menuai.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from menuai.components.tesla_fleet.const import (
    AUTHORIZE_URL,
    DOMAIN,
    SCOPES,
    TOKEN_URL,
)
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import config_entry_oauth2_flow
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

REDIRECT = "https://example.com/auth/external/callback"
UNIQUE_ID = "uid"


@pytest.fixture
async def access_token(menuai: menuai) -> str:
    """Return a valid access token."""
    return config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "sub": UNIQUE_ID,
            "aud": [],
            "scp": [
                "vehicle_device_data",
                "vehicle_cmds",
                "vehicle_charging_cmds",
                "energy_device_data",
                "energy_cmds",
                "offline_access",
                "openid",
            ],
            "ou_code": "NA",
        },
    )


@pytest.fixture(autouse=True)
async def create_credential(menuai: menuai) -> None:
    """Create a user credential."""
    # Create user application credential
    assert await async_setup_component(menuai, "application_credentials", {})
    await async_import_client_credential(
        menuai,
        DOMAIN,
        ClientCredential("user_client_id", "user_client_secret"),
        "user_cred",
    )


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow_user_cred(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    access_token: str,
) -> None:
    """Check full flow."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.EXTERNAL_STEP

    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": REDIRECT,
        },
    )

    assert result["url"].startswith(AUTHORIZE_URL)
    parsed_url = urlparse(result["url"])
    parsed_query = parse_qs(parsed_url.query)
    assert parsed_query["response_type"][0] == "code"
    assert parsed_query["client_id"][0] == "user_client_id"
    assert parsed_query["redirect_uri"][0] == REDIRECT
    assert parsed_query["state"][0] == state
    assert parsed_query["scope"][0] == " ".join(SCOPES)
    assert "code_challenge" not in parsed_query  # Ensure not a PKCE flow

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        TOKEN_URL,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": access_token,
            "type": "Bearer",
            "expires_in": 60,
        },
    )
    with patch(
        "menuai.components.tesla_fleet.async_setup_entry", return_value=True
    ) as mock_setup:
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == UNIQUE_ID
    assert "result" in result
    assert result["result"].unique_id == UNIQUE_ID
    assert "token" in result["result"].data
    assert result["result"].data["token"]["access_token"] == access_token
    assert result["result"].data["token"]["refresh_token"] == "mock-refresh-token"


@pytest.mark.usefixtures("current_request_with_host")
async def test_reauthentication(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    access_token: str,
) -> None:
    """Test Tesla Fleet reauthentication."""
    old_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=UNIQUE_ID,
        version=1,
        data={},
    )
    old_entry.add_to_menuai(menuai)

    result = await old_entry.start_reauth_flow(menuai)

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    result = await menuai.config_entries.flow.async_configure(flows[0]["flow_id"], {})

    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": REDIRECT,
        },
    )
    client = await menuai_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        TOKEN_URL,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": access_token,
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch(
        "menuai.components.tesla_fleet.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert result
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


@pytest.mark.usefixtures("current_request_with_host")
async def test_reauth_account_mismatch(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    access_token: str,
) -> None:
    """Test Tesla Fleet reauthentication with different account."""
    old_entry = MockConfigEntry(domain=DOMAIN, unique_id="baduid", version=1, data={})
    old_entry.add_to_menuai(menuai)

    result = await old_entry.start_reauth_flow(menuai)

    flows = menuai.config_entries.flow.async_progress()
    result = await menuai.config_entries.flow.async_configure(flows[0]["flow_id"], {})

    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": REDIRECT,
        },
    )
    client = await menuai_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        TOKEN_URL,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": access_token,
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch(
        "menuai.components.tesla_fleet.async_setup_entry", return_value=True
    ):
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_account_mismatch"
