"""Test the Miele config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock

from pymiele import OAUTH2_AUTHORIZE, OAUTH2_TOKEN
import pytest

from menuai.components.miele.const import DOMAIN
from menuai.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import config_entry_oauth2_flow

from .const import CLIENT_ID

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

REDIRECT_URL = "https://example.com/auth/external/callback"

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    mock_setup_entry: Generator[AsyncMock],
) -> None:
    """Check full flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
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
        "&vg=sv-SE"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert result.get("type") is FlowResultType.EXTERNAL_STEP
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("current_request_with_host")
async def test_flow_reauth_abort(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    access_token: str,
    expires_at: float,
) -> None:
    """Test reauth step with correct params."""

    CURRENT_TOKEN = {
        "auth_implementation": DOMAIN,
        "token": {
            "access_token": access_token,
            "expires_in": 86399,
            "refresh_token": "3012bc9f-7a65-4240-b817-9154ffdcc30f",
            "token_type": "Bearer",
            "expires_at": expires_at,
        },
    }
    assert menuai.config_entries.async_update_entry(
        mock_config_entry,
        data=CURRENT_TOKEN,
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
        "&vg=sv-SE"
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
        },
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    await menuai.async_block_till_done()

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "reauth_successful"

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1


@pytest.mark.usefixtures("current_request_with_host")
async def test_flow_reconfigure_abort(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    access_token: str,
    expires_at: float,
) -> None:
    """Test reconfigure step with correct params."""

    CURRENT_TOKEN = {
        "auth_implementation": DOMAIN,
        "token": {
            "access_token": access_token,
            "expires_in": 86399,
            "refresh_token": "3012bc9f-7a65-4240-b817-9154ffdcc30f",
            "token_type": "Bearer",
            "expires_at": expires_at,
        },
    }
    assert menuai.config_entries.async_update_entry(
        mock_config_entry,
        data=CURRENT_TOKEN,
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
        "&vg=sv-SE"
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
        },
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    await menuai.async_block_till_done()

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1


@pytest.mark.usefixtures("current_request_with_host")
async def test_zeroconf_flow(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    mock_setup_entry: Generator[AsyncMock],
) -> None:
    """Test zeroconf flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "oauth_discovery"
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {},
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
        "&vg=sv-SE"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    assert result.get("type") is FlowResultType.EXTERNAL_STEP

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup_entry.mock_calls) == 1
    assert result["type"] is FlowResultType.CREATE_ENTRY

    config_entry = result["result"]
    assert config_entry.domain == "miele"
