"""Test yolink config flow."""

from http import HTTPStatus
from unittest.mock import patch

import pytest
from yolink.const import OAUTH2_AUTHORIZE, OAUTH2_TOKEN

from menuai import config_entries, setup
from menuai.components import application_credentials
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import config_entry_oauth2_flow

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

CLIENT_ID = "12345"
CLIENT_SECRET = "6789"
DOMAIN = "yolink"


async def test_abort_if_no_configuration(menuai: menuai) -> None:
    """Check flow abort when no configuration."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "missing_credentials"


async def test_abort_if_existing_entry(menuai: menuai) -> None:
    """Check flow abort when an entry already exist."""
    MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN).add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Check full flow."""
    assert await setup.async_setup_component(
        menuai,
        DOMAIN,
        {},
    )
    await application_credentials.async_import_client_credential(
        menuai,
        DOMAIN,
        application_credentials.ClientCredential(CLIENT_ID, CLIENT_SECRET),
    )
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
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
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        "&redirect_uri=https://example.com/auth/external/callback"
        f"&state={state}&scope=create"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == HTTPStatus.OK
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

    with (
        patch("menuai.components.yolink.api.ConfigEntryAuth"),
        patch(
            "menuai.components.yolink.async_setup_entry", return_value=True
        ) as mock_setup,
    ):
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert result["data"]["auth_implementation"] == DOMAIN

    result["data"]["token"].pop("expires_at")
    assert result["data"]["token"] == {
        "refresh_token": "mock-refresh-token",
        "access_token": "mock-access-token",
        "type": "Bearer",
        "expires_in": 60,
    }

    assert DOMAIN in menuai.config.components
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1


@pytest.mark.usefixtures("current_request_with_host")
async def test_abort_if_authorization_timeout(menuai: menuai) -> None:
    """Check yolink authorization timeout."""
    assert await setup.async_setup_component(
        menuai,
        DOMAIN,
        {},
    )
    await application_credentials.async_import_client_credential(
        menuai,
        DOMAIN,
        application_credentials.ClientCredential(CLIENT_ID, CLIENT_SECRET),
    )
    with patch(
        "menuai.components.yolink.config_entry_oauth2_flow."
        "LocalOAuth2Implementation.async_generate_authorize_url",
        side_effect=TimeoutError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "authorize_url_timeout"


@pytest.mark.usefixtures("current_request_with_host")
async def test_reauthentication(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test yolink reauthentication."""
    await setup.async_setup_component(
        menuai,
        DOMAIN,
        {},
    )

    await application_credentials.async_import_client_credential(
        menuai,
        DOMAIN,
        application_credentials.ClientCredential(CLIENT_ID, CLIENT_SECRET),
    )

    old_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        version=1,
        data={
            "refresh_token": "outdated_fresh_token",
            "access_token": "outdated_access_token",
        },
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
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )
    client = await menuai_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with (
        patch("menuai.components.yolink.api.ConfigEntryAuth"),
        patch(
            "menuai.components.yolink.async_setup_entry", return_value=True
        ) as mock_setup,
    ):
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    token_data = old_entry.data["token"]
    assert token_data["access_token"] == "mock-access-token"
    assert token_data["refresh_token"] == "mock-refresh-token"
    assert token_data["type"] == "Bearer"
    assert token_data["expires_in"] == 60
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(mock_setup.mock_calls) == 1
