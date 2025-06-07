"""Test the xbox config flow."""

from http import HTTPStatus
from unittest.mock import patch

import pytest

from menuai import config_entries, setup
from menuai.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from menuai.components.xbox.const import DOMAIN, OAUTH2_AUTHORIZE, OAUTH2_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import config_entry_oauth2_flow

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

CLIENT_ID = "1234"
CLIENT_SECRET = "5678"


async def test_abort_if_existing_entry(menuai: menuai) -> None:
    """Check flow abort when an entry already exist."""
    MockConfigEntry(domain=DOMAIN).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        "xbox", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Check full flow."""
    assert await setup.async_setup_component(menuai, "application_credentials", {})
    await async_import_client_credential(
        menuai, DOMAIN, ClientCredential(CLIENT_ID, CLIENT_SECRET), "imported-cred"
    )

    result = await menuai.config_entries.flow.async_init(
        "xbox", context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )

    scope = "Xboxlive.signin+Xboxlive.offline_access"

    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        "&redirect_uri=https://example.com/auth/external/callback"
        f"&state={state}&scope={scope}"
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

    with patch(
        "menuai.components.xbox.async_setup_entry", return_value=True
    ) as mock_setup:
        await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1
