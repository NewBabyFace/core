"""Tests for the Toon config flow."""

from http import HTTPStatus
from unittest.mock import patch

import pytest
from toonapi import Agreement, ToonError

from menuai.components.toon.const import CONF_AGREEMENT, DOMAIN
from menuai.config_entries import SOURCE_IMPORT, SOURCE_USER
from menuai.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import config_entry_oauth2_flow
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator


async def setup_component(menuai: menuai) -> None:
    """Set up Toon component."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com"},
    )

    with patch("os.path.isfile", return_value=False):
        assert await async_setup_component(
            menuai,
            DOMAIN,
            {DOMAIN: {CONF_CLIENT_ID: "client", CONF_CLIENT_SECRET: "secret"}},
        )
        await menuai.async_block_till_done()


async def test_abort_if_no_configuration(menuai: menuai) -> None:
    """Test abort if no app is configured."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "missing_configuration"


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow_implementation(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test registering an integration and finishing flow works."""
    await setup_component(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pick_implementation"

    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"implementation": "eneco"}
    )

    assert result2["type"] is FlowResultType.EXTERNAL_STEP
    assert result2["url"] == (
        "https://api.toon.eu/authorize"
        "?response_type=code&client_id=client"
        "&redirect_uri=https://example.com/auth/external/callback"
        f"&state={state}"
        "&tenant_id=eneco&issuer=identity.toon.eu"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == HTTPStatus.OK
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        "https://api.toon.eu/token",
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch("toonapi.Toon.agreements", return_value=[Agreement(agreement_id=123)]):
        result3 = await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert result3["data"]["auth_implementation"] == "eneco"
    assert result3["data"]["agreement_id"] == 123
    result3["data"]["token"].pop("expires_at")
    assert result3["data"]["token"] == {
        "refresh_token": "mock-refresh-token",
        "access_token": "mock-access-token",
        "type": "Bearer",
        "expires_in": 60,
    }


@pytest.mark.usefixtures("current_request_with_host")
async def test_no_agreements(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test abort when there are no displays."""
    await setup_component(menuai)
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
    await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"implementation": "eneco"}
    )

    client = await menuai_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")
    aioclient_mock.post(
        "https://api.toon.eu/token",
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch("toonapi.Toon.agreements", return_value=[]):
        result3 = await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "no_agreements"


@pytest.mark.usefixtures("current_request_with_host")
async def test_multiple_agreements(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test abort when there are no displays."""
    await setup_component(menuai)
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
    await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"implementation": "eneco"}
    )

    client = await menuai_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        "https://api.toon.eu/token",
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch(
        "toonapi.Toon.agreements",
        return_value=[Agreement(agreement_id=1), Agreement(agreement_id=2)],
    ):
        result3 = await menuai.config_entries.flow.async_configure(result["flow_id"])

        assert result3["type"] is FlowResultType.FORM
        assert result3["step_id"] == "agreement"

        result4 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_AGREEMENT: "None None, None"}
        )
        assert result4["data"]["auth_implementation"] == "eneco"
        assert result4["data"]["agreement_id"] == 1


@pytest.mark.usefixtures("current_request_with_host")
async def test_agreement_already_set_up(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test showing display form again if display already exists."""
    await setup_component(menuai)
    MockConfigEntry(domain=DOMAIN, unique_id=123).add_to_menuai(menuai)
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
    await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"implementation": "eneco"}
    )

    client = await menuai_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")
    aioclient_mock.post(
        "https://api.toon.eu/token",
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch("toonapi.Toon.agreements", return_value=[Agreement(agreement_id=123)]):
        result3 = await menuai.config_entries.flow.async_configure(result["flow_id"])

        assert result3["type"] is FlowResultType.ABORT
        assert result3["reason"] == "already_configured"


@pytest.mark.usefixtures("current_request_with_host")
async def test_toon_abort(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test we abort on Toon error."""
    await setup_component(menuai)
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
    await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"implementation": "eneco"}
    )

    client = await menuai_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")
    aioclient_mock.post(
        "https://api.toon.eu/token",
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch("toonapi.Toon.agreements", side_effect=ToonError):
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"])

        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "connection_error"


@pytest.mark.usefixtures("current_request_with_host")
async def test_import(menuai: menuai) -> None:
    """Test if importing step works."""
    await setup_component(menuai)

    # Setting up the component without entries, should already have triggered
    # it. Hence, expect this to throw an already_in_progress.
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_in_progress"


@pytest.mark.usefixtures("current_request_with_host")
async def test_import_migration(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test if importing step with migration works."""
    old_entry = MockConfigEntry(domain=DOMAIN, unique_id=123, version=1)
    old_entry.add_to_menuai(menuai)

    await setup_component(menuai)

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].version == 1

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    flow = menuai.config_entries.flow._progress[flows[0]["flow_id"]]
    assert flow.migrate_entry == old_entry.entry_id

    state = config_entry_oauth2_flow._encode_jwt(
        menuai,
        {
            "flow_id": flows[0]["flow_id"],
            "redirect_uri": "https://example.com/auth/external/callback",
        },
    )
    await menuai.config_entries.flow.async_configure(
        flows[0]["flow_id"], {"implementation": "eneco"}
    )

    client = await menuai_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")
    aioclient_mock.post(
        "https://api.toon.eu/token",
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch("toonapi.Toon.agreements", return_value=[Agreement(agreement_id=123)]):
        result = await menuai.config_entries.flow.async_configure(flows[0]["flow_id"])

    assert result["type"] is FlowResultType.CREATE_ENTRY

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].version == 2
