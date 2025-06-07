"""Tests for diagnostics platform of local calendar."""

from aiohttp.test_utils import TestClient
from freezegun import freeze_time
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.auth.models import Credentials
from menuai.core import menuai

from .conftest import TEST_ENTITY, Client

from tests.common import CLIENT_ID, MockConfigEntry, MockUser
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator, WebSocketGenerator


async def generate_new_menuai_access_token(
    menuai: menuai, menuai_admin_user: MockUser, menuai_admin_credential: Credentials
) -> str:
    """Return an access token to access MenuAI."""
    await menuai.auth.async_link_user(menuai_admin_user, menuai_admin_credential)

    refresh_token = await menuai.auth.async_create_refresh_token(
        menuai_admin_user, CLIENT_ID, credential=menuai_admin_credential
    )
    return menuai.auth.async_create_access_token(refresh_token)


def _get_test_client_generator(
    menuai: menuai, aiohttp_client: ClientSessionGenerator, new_token: str
):
    """Return a test client generator.""."""

    async def auth_client() -> TestClient:
        return await aiohttp_client(
            menuai.http.app, headers={"Authorization": f"Bearer {new_token}"}
        )

    return auth_client


@freeze_time("2023-03-13 12:05:00-07:00")
@pytest.mark.usefixtures("socket_enabled")
async def test_empty_calendar(
    menuai: menuai,
    setup_integration: None,
    menuai_admin_user: MockUser,
    menuai_admin_credential: Credentials,
    config_entry: MockConfigEntry,
    aiohttp_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics against an empty calendar."""
    # Since we are freezing time only when we enter this test, we need to
    # manually create a new token and clients since the token created by
    # the fixtures would not be valid.
    #
    # Ideally we would use pytest.mark.freeze_time before the fixtures, but that does not
    # work with the ical library and freezegun because
    # `TypeError: '<' not supported between instances of 'FakeDatetimeMeta' and 'FakeDateMeta'`
    new_token = await generate_new_menuai_access_token(
        menuai, menuai_admin_user, menuai_admin_credential
    )
    data = await get_diagnostics_for_config_entry(
        menuai, _get_test_client_generator(menuai, aiohttp_client, new_token), config_entry
    )
    assert data == snapshot


@freeze_time("2023-03-13 12:05:00-07:00")
@pytest.mark.usefixtures("socket_enabled")
async def test_api_date_time_event(
    menuai: menuai,
    setup_integration: None,
    menuai_admin_user: MockUser,
    menuai_admin_credential: Credentials,
    config_entry: MockConfigEntry,
    menuai_ws_client: WebSocketGenerator,
    aiohttp_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test an event with a start/end date time."""
    # Since we are freezing time only when we enter this test, we need to
    # manually create a new token and clients since the token created by
    # the fixtures would not be valid.
    #
    # Ideally we would use pytest.mark.freeze_time before the fixtures, but that does not
    # work with the ical library and freezegun because
    # `TypeError: '<' not supported between instances of 'FakeDatetimeMeta' and 'FakeDateMeta'`
    new_token = await generate_new_menuai_access_token(
        menuai, menuai_admin_user, menuai_admin_credential
    )
    client = Client(await menuai_ws_client(menuai, access_token=new_token))
    await client.cmd_result(
        "create",
        {
            "entity_id": TEST_ENTITY,
            "event": {
                "summary": "Bastille Day Party",
                "dtstart": "1997-07-14T17:00:00+00:00",
                "dtend": "1997-07-15T04:00:00+00:00",
                "rrule": "FREQ=DAILY",
            },
        },
    )

    data = await get_diagnostics_for_config_entry(
        menuai, _get_test_client_generator(menuai, aiohttp_client, new_token), config_entry
    )
    assert data == snapshot
