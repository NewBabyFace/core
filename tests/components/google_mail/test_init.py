"""Tests for Google Mail."""

import http
import time
from unittest.mock import patch

from aiohttp.client_exceptions import ClientError
import pytest

from menuai.components.google_mail import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .conftest import GOOGLE_TOKEN_URI, ComponentSetup

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_setup_success(
    menuai: menuai, setup_integration: ComponentSetup
) -> None:
    """Test successful setup and unload."""
    await setup_integration()

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entries[0].entry_id)
    await menuai.async_block_till_done()

    assert not menuai.services.async_services().get(DOMAIN)


@pytest.mark.parametrize("expires_at", [time.time() - 3600], ids=["expired"])
async def test_expired_token_refresh_success(
    menuai: menuai,
    setup_integration: ComponentSetup,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test expired token is refreshed."""

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        GOOGLE_TOKEN_URI,
        json={
            "access_token": "updated-access-token",
            "refresh_token": "updated-refresh-token",
            "expires_at": time.time() + 3600,
            "expires_in": 3600,
        },
    )

    await setup_integration()

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED
    assert entries[0].data["token"]["access_token"] == "updated-access-token"
    assert entries[0].data["token"]["expires_in"] == 3600


@pytest.mark.parametrize(
    ("expires_at", "status", "expected_state"),
    [
        (
            time.time() - 3600,
            http.HTTPStatus.UNAUTHORIZED,
            ConfigEntryState.SETUP_ERROR,
        ),
        (
            time.time() - 3600,
            http.HTTPStatus.INTERNAL_SERVER_ERROR,
            ConfigEntryState.SETUP_RETRY,
        ),
        (
            time.time() - 3600,
            http.HTTPStatus.BAD_REQUEST,
            ConfigEntryState.SETUP_ERROR,
        ),
    ],
    ids=["failure_requires_reauth", "transient_failure", "revoked_auth"],
)
async def test_expired_token_refresh_failure(
    menuai: menuai,
    setup_integration: ComponentSetup,
    aioclient_mock: AiohttpClientMocker,
    status: http.HTTPStatus,
    expected_state: ConfigEntryState,
) -> None:
    """Test failure while refreshing token with a transient error."""

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        GOOGLE_TOKEN_URI,
        status=status,
    )

    await setup_integration()

    # Verify a transient failure has occurred
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries[0].state is expected_state


async def test_expired_token_refresh_client_error(
    menuai: menuai,
    setup_integration: ComponentSetup,
) -> None:
    """Test failure while refreshing token with a client error."""

    with patch(
        "menuai.components.google_mail.OAuth2Session.async_ensure_token_valid",
        side_effect=ClientError,
    ):
        await setup_integration()

    # Verify a transient failure has occurred
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries[0].state is ConfigEntryState.SETUP_RETRY


async def test_device_info(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    setup_integration: ComponentSetup,
) -> None:
    """Test device info."""
    await setup_integration()

    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    assert device.entry_type is dr.DeviceEntryType.SERVICE
    assert device.identifiers == {(DOMAIN, entry.entry_id)}
    assert device.manufacturer == "Google, Inc."
    assert device.name == "example@gmail.com"
