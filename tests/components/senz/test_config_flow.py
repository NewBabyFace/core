"""Test the SENZ config flow."""

from unittest.mock import patch

from aiosenz import AUTHORIZATION_ENDPOINT, TOKEN_ENDPOINT
import pytest

from menuai import config_entries
from menuai.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from menuai.components.senz.const import DOMAIN
from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow
from menuai.setup import async_setup_component

from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

CLIENT_ID = "1234"
CLIENT_SECRET = "5678"


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Check full flow."""
    await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()

    await async_import_client_credential(
        menuai, DOMAIN, ClientCredential(CLIENT_ID, CLIENT_SECRET), "cred"
    )

    result = await menuai.config_entries.flow.async_init(
        "senz", context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )

    assert result["url"] == (
        f"{AUTHORIZATION_ENDPOINT}?response_type=code&client_id={CLIENT_ID}"
        "&redirect_uri=https://example.com/auth/external/callback"
        f"&state={state}&scope=restapi+offline_access"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        TOKEN_ENDPOINT,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch(
        "menuai.components.senz.async_setup_entry", return_value=True
    ) as mock_setup:
        await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1
