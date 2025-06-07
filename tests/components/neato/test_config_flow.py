"""Test the Neato Botvac config flow."""

from unittest.mock import patch

from pybotvac.neato import Neato
import pytest

from menuai import config_entries, setup
from menuai.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from menuai.components.neato.const import NEATO_DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import config_entry_oauth2_flow

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

CLIENT_ID = "1234"
CLIENT_SECRET = "5678"

VENDOR = Neato()
OAUTH2_AUTHORIZE = VENDOR.auth_endpoint
OAUTH2_TOKEN = VENDOR.token_endpoint


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Check full flow."""
    assert await setup.async_setup_component(menuai, "neato", {})
    await async_import_client_credential(
        menuai, NEATO_DOMAIN, ClientCredential(CLIENT_ID, CLIENT_SECRET)
    )

    result = await menuai.config_entries.flow.async_init(
        "neato", context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )

    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        "&redirect_uri=https://example.com/auth/external/callback"
        f"&state={state}"
        f"&client_secret={CLIENT_SECRET}"
        "&scope=public_profile+control_robots+maps"
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

    with patch(
        "menuai.components.neato.async_setup_entry", return_value=True
    ) as mock_setup:
        await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert len(menuai.config_entries.async_entries(NEATO_DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1


async def test_abort_if_already_setup(menuai: menuai) -> None:
    """Test we abort if Neato is already setup."""
    entry = MockConfigEntry(
        domain=NEATO_DOMAIN,
        data={"auth_implementation": "neato", "token": {"some": "data"}},
    )
    entry.add_to_menuai(menuai)

    # Should fail
    result = await menuai.config_entries.flow.async_init(
        "neato", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("current_request_with_host")
async def test_reauth(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test initialization of the reauth flow."""
    assert await setup.async_setup_component(menuai, "neato", {})
    await async_import_client_credential(
        menuai, NEATO_DOMAIN, ClientCredential(CLIENT_ID, CLIENT_SECRET)
    )

    entry = MockConfigEntry(
        entry_id="my_entry",
        domain=NEATO_DOMAIN,
        data={"username": "abcdef", "password": "123456", "vendor": "neato"},
    )
    entry.add_to_menuai(menuai)

    # Should show form
    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    # Confirm reauth flow
    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})

    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    # Update entry
    with patch(
        "menuai.components.neato.async_setup_entry", return_value=True
    ) as mock_setup:
        result3 = await menuai.config_entries.flow.async_configure(result2["flow_id"])
        await menuai.async_block_till_done()

    new_entry = menuai.config_entries.async_get_entry("my_entry")

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "reauth_successful"
    assert new_entry.state is ConfigEntryState.LOADED
    assert len(menuai.config_entries.async_entries(NEATO_DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1
