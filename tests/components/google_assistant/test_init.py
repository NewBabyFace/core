"""The tests for google-assistant init."""

from http import HTTPStatus

from menuai.components import google_assistant as ga
from menuai.core import Context, menuai
from menuai.setup import async_setup_component

from .test_http import DUMMY_CONFIG

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_import(menuai: menuai) -> None:
    """Test import."""

    await async_setup_component(
        menuai,
        ga.DOMAIN,
        {"google_assistant": DUMMY_CONFIG},
    )

    entries = menuai.config_entries.async_entries("google_assistant")
    assert len(entries) == 1
    assert entries[0].data[ga.const.CONF_PROJECT_ID] == "1234"


async def test_import_changed(menuai: menuai) -> None:
    """Test import with changed project id."""

    old_entry = MockConfigEntry(
        domain=ga.DOMAIN, data={ga.const.CONF_PROJECT_ID: "4321"}, source="import"
    )
    old_entry.add_to_menuai(menuai)

    await async_setup_component(
        menuai,
        ga.DOMAIN,
        {"google_assistant": DUMMY_CONFIG},
    )
    await menuai.async_block_till_done()

    entries = menuai.config_entries.async_entries("google_assistant")
    assert len(entries) == 1
    assert entries[0].data[ga.const.CONF_PROJECT_ID] == "1234"


async def test_request_sync_service(
    aioclient_mock: AiohttpClientMocker, menuai: menuai
) -> None:
    """Test that it posts to the request_sync url."""
    aioclient_mock.post(
        ga.const.HOMEGRAPH_TOKEN_URL,
        status=HTTPStatus.OK,
        json={"access_token": "1234", "expires_in": 3600},
    )

    aioclient_mock.post(ga.const.REQUEST_SYNC_BASE_URL, status=HTTPStatus.OK)

    await async_setup_component(
        menuai,
        "google_assistant",
        {"google_assistant": DUMMY_CONFIG},
    )

    assert aioclient_mock.call_count == 0
    await menuai.services.async_call(
        ga.const.DOMAIN,
        ga.const.SERVICE_REQUEST_SYNC,
        blocking=True,
        context=Context(user_id="123"),
    )

    assert aioclient_mock.call_count == 2  # token + request
