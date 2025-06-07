"""Tests for Twitch."""

import http
import time
from unittest.mock import AsyncMock, patch

from aiohttp.client_exceptions import ClientError
import pytest

from menuai.components.twitch.const import DOMAIN, OAUTH2_TOKEN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_setup_success(
    menuai: menuai, config_entry: MockConfigEntry, twitch_mock: AsyncMock
) -> None:
    """Test successful setup and unload."""
    await setup_integration(menuai, config_entry)

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entries[0].entry_id)
    await menuai.async_block_till_done()

    assert not menuai.services.async_services().get(DOMAIN)


@pytest.mark.parametrize("expires_at", [time.time() - 3600], ids=["expired"])
async def test_expired_token_refresh_success(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    twitch_mock: AsyncMock,
) -> None:
    """Test expired token is refreshed."""

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "access_token": "updated-access-token",
            "refresh_token": "updated-refresh-token",
            "expires_at": time.time() + 3600,
            "expires_in": 3600,
        },
    )

    await setup_integration(menuai, config_entry)

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
    ],
    ids=["failure_requires_reauth", "transient_failure"],
)
async def test_expired_token_refresh_failure(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    status: http.HTTPStatus,
    expected_state: ConfigEntryState,
    config_entry: MockConfigEntry,
    twitch_mock: AsyncMock,
) -> None:
    """Test failure while refreshing token with a transient error."""

    aioclient_mock.clear_requests()
    aioclient_mock.post(
        OAUTH2_TOKEN,
        status=status,
    )
    config_entry.add_to_menuai(menuai)

    assert not await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Verify a transient failure has occurred
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries[0].state is expected_state


async def test_expired_token_refresh_client_error(
    menuai: menuai, config_entry: MockConfigEntry, twitch_mock: AsyncMock
) -> None:
    """Test failure while refreshing token with a client error."""

    with patch(
        "menuai.components.twitch.OAuth2Session.async_ensure_token_valid",
        side_effect=ClientError,
    ):
        config_entry.add_to_menuai(menuai)

        assert not await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    # Verify a transient failure has occurred
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries[0].state is ConfigEntryState.SETUP_RETRY
