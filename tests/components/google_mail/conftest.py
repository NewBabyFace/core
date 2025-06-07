"""Configure tests for the Google Mail integration."""

from collections.abc import Awaitable, Callable, Coroutine
import time
from typing import Any
from unittest.mock import patch

from httplib2 import Response
import pytest

from menuai.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from menuai.components.google_mail.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

type ComponentSetup = Callable[[], Awaitable[None]]

BUILD = "menuai.components.google_mail.api.build"
CLIENT_ID = "1234"
CLIENT_SECRET = "5678"
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]
SENSOR = "sensor.example_gmail_com_vacation_end_date"
TITLE = "example@gmail.com"
TOKEN = "menuai.components.google_mail.api.config_entry_oauth2_flow.OAuth2Session.async_ensure_token_valid"


@pytest.fixture(name="scopes")
def mock_scopes() -> list[str]:
    """Fixture to set the scopes present in the OAuth token."""
    return SCOPES


@pytest.fixture(autouse=True)
async def setup_credentials(menuai: menuai) -> None:
    """Fixture to setup credentials."""
    assert await async_setup_component(menuai, "application_credentials", {})
    await async_import_client_credential(
        menuai,
        DOMAIN,
        ClientCredential(CLIENT_ID, CLIENT_SECRET),
        DOMAIN,
    )


@pytest.fixture(name="expires_at")
def mock_expires_at() -> int:
    """Fixture to set the oauth token expiration time."""
    return time.time() + 3600


@pytest.fixture(name="config_entry")
def mock_config_entry(expires_at: int, scopes: list[str]) -> MockConfigEntry:
    """Create Google Mail entry in MenuAI."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        unique_id=TITLE,
        data={
            "auth_implementation": DOMAIN,
            "token": {
                "access_token": "mock-access-token",
                "refresh_token": "mock-refresh-token",
                "expires_at": expires_at,
                "scope": " ".join(scopes),
            },
        },
    )


@pytest.fixture(autouse=True)
def mock_connection(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock Google Mail connection."""
    aioclient_mock.post(
        GOOGLE_TOKEN_URI,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": "mock-access-token",
            "type": "Bearer",
            "expires_in": 60,
        },
    )


@pytest.fixture(name="setup_integration")
async def mock_setup_integration(
    menuai: menuai, config_entry: MockConfigEntry
) -> Callable[[], Coroutine[Any, Any, None]]:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    assert await async_setup_component(menuai, "application_credentials", {})
    await async_import_client_credential(
        menuai,
        DOMAIN,
        ClientCredential(CLIENT_ID, CLIENT_SECRET),
        DOMAIN,
    )

    async def func() -> None:
        with patch(
            "httplib2.Http.request",
            return_value=(
                Response({}),
                bytes(
                    await async_load_fixture(menuai, "get_vacation.json", DOMAIN),
                    encoding="UTF-8",
                ),
            ),
        ):
            assert await async_setup_component(menuai, DOMAIN, {})
            await menuai.async_block_till_done()

    return func
