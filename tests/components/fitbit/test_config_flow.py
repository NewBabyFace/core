"""Test the fitbit config flow."""

from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any
from unittest.mock import patch

import pytest
from requests_mock.mocker import Mocker

from menuai import config_entries
from menuai.components.fitbit.const import DOMAIN, OAUTH2_AUTHORIZE, OAUTH2_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import config_entry_oauth2_flow

from .conftest import (
    CLIENT_ID,
    DISPLAY_NAME,
    FAKE_AUTH_IMPL,
    PROFILE_API_URL,
    PROFILE_DATA,
    PROFILE_USER_ID,
    SERVER_ACCESS_TOKEN,
)

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator

REDIRECT_URL = "https://example.com/auth/external/callback"


@pytest.mark.usefixtures("current_request_with_host")
async def test_full_flow(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    profile: None,
    setup_credentials: None,
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
    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URL}"
        f"&state={state}"
        "&scope=activity+heartrate+nutrition+profile+settings+sleep+weight&prompt=consent"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json=SERVER_ACCESS_TOKEN,
    )

    with patch(
        "menuai.components.fitbit.async_setup_entry", return_value=True
    ) as mock_setup:
        await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert len(mock_setup.mock_calls) == 1
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    config_entry = entries[0]
    assert config_entry.title == DISPLAY_NAME
    assert config_entry.unique_id == PROFILE_USER_ID

    data = dict(config_entry.data)
    assert "token" in data
    del data["token"]["expires_at"]
    assert dict(config_entry.data) == {
        "auth_implementation": FAKE_AUTH_IMPL,
        "token": SERVER_ACCESS_TOKEN,
    }


@pytest.mark.parametrize(
    ("status_code", "error_reason"),
    [
        (HTTPStatus.UNAUTHORIZED, "invalid_auth"),
        (HTTPStatus.INTERNAL_SERVER_ERROR, "cannot_connect"),
    ],
)
@pytest.mark.usefixtures("current_request_with_host")
async def test_token_error(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    profile: None,
    setup_credentials: None,
    status_code: HTTPStatus,
    error_reason: str,
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
    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URL}"
        f"&state={state}"
        "&scope=activity+heartrate+nutrition+profile+settings+sleep+weight&prompt=consent"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        status=status_code,
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == error_reason


@pytest.mark.parametrize(
    ("http_status", "json", "error_reason"),
    [
        (HTTPStatus.INTERNAL_SERVER_ERROR, None, "cannot_connect"),
        (HTTPStatus.FORBIDDEN, None, "cannot_connect"),
        (
            HTTPStatus.UNAUTHORIZED,
            {
                "errors": [{"errorType": "invalid_grant"}],
            },
            "invalid_access_token",
        ),
    ],
)
@pytest.mark.usefixtures("current_request_with_host")
async def test_api_failure(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    requests_mock: Mocker,
    setup_credentials: None,
    http_status: HTTPStatus,
    json: Any,
    error_reason: str,
) -> None:
    """Test a failure to fetch the profile during the setup flow."""
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
    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URL}"
        f"&state={state}"
        "&scope=activity+heartrate+nutrition+profile+settings+sleep+weight&prompt=consent"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json=SERVER_ACCESS_TOKEN,
    )

    requests_mock.register_uri(
        "GET",
        PROFILE_API_URL,
        status_code=http_status,
        json=json,
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == error_reason


@pytest.mark.usefixtures("current_request_with_host")
async def test_config_entry_already_exists(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    setup_credentials: None,
    integration_setup: Callable[[], Awaitable[bool]],
    config_entry: MockConfigEntry,
) -> None:
    """Test that an account may only be configured once."""

    # Verify existing config entry
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

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
    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URL}"
        f"&state={state}"
        "&scope=activity+heartrate+nutrition+profile+settings+sleep+weight&prompt=consent"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json=SERVER_ACCESS_TOKEN,
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


@pytest.mark.usefixtures("current_request_with_host")
async def test_reauth_flow(
    menuai: menuai,
    config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    profile: None,
    setup_credentials: None,
) -> None:
    """Test OAuth reauthentication flow will update existing config entry."""
    config_entry.add_to_menuai(menuai)

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

    # config_entry.req initiates reauth
    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        flow_id=result["flow_id"],
        user_input={},
    )
    assert result["type"] is FlowResultType.EXTERNAL_STEP
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
        "&scope=activity+heartrate+nutrition+profile+settings+sleep+weight&prompt=none"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "updated-refresh-token",
            "access_token": "updated-access-token",
            "type": "Bearer",
            "expires_in": "60",
        },
    )

    with patch(
        "menuai.components.fitbit.async_setup_entry", return_value=True
    ) as mock_setup:
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "reauth_successful"

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1

    assert config_entry.data["token"]["refresh_token"] == "updated-refresh-token"


@pytest.mark.parametrize("profile_id", ["other-user-id"])
@pytest.mark.usefixtures("current_request_with_host")
async def test_reauth_wrong_user_id(
    menuai: menuai,
    config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    profile: None,
    setup_credentials: None,
) -> None:
    """Test OAuth reauthentication where the wrong user is selected."""
    config_entry.add_to_menuai(menuai)

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        flow_id=result["flow_id"],
        user_input={},
    )
    assert result["type"] is FlowResultType.EXTERNAL_STEP
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
        "&scope=activity+heartrate+nutrition+profile+settings+sleep+weight&prompt=none"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "updated-refresh-token",
            "access_token": "updated-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch(
        "menuai.components.fitbit.async_setup_entry", return_value=True
    ) as mock_setup:
        result = await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "wrong_account"

    assert len(mock_setup.mock_calls) == 0


@pytest.mark.parametrize(
    ("profile_data", "expected_title"),
    [
        (PROFILE_DATA, DISPLAY_NAME),
        ({"displayName": DISPLAY_NAME}, DISPLAY_NAME),
    ],
    ids=("full_profile_data", "display_name_only"),
)
@pytest.mark.usefixtures("current_request_with_host")
async def test_partial_profile_data(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    profile: None,
    setup_credentials: None,
    expected_title: str,
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
    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["url"] == (
        f"{OAUTH2_AUTHORIZE}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URL}"
        f"&state={state}"
        "&scope=activity+heartrate+nutrition+profile+settings+sleep+weight&prompt=consent"
    )

    client = await menuai_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json=SERVER_ACCESS_TOKEN,
    )

    with patch(
        "menuai.components.fitbit.async_setup_entry", return_value=True
    ) as mock_setup:
        await menuai.config_entries.flow.async_configure(result["flow_id"])

    assert len(mock_setup.mock_calls) == 1
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    config_entry = entries[0]
    assert config_entry.title == expected_title
