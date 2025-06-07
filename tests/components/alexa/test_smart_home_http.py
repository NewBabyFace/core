"""Test Smart Home HTTP endpoints."""

from http import HTTPStatus
import json
import logging
from typing import Any

from aiohttp import ClientResponse
import pytest

from menuai.components.alexa import DOMAIN, smart_home
from menuai.const import CONTENT_TYPE_JSON
from menuai.core import menuai
from menuai.setup import async_setup_component

from .test_common import get_new_request

from tests.typing import ClientSessionGenerator


async def do_http_discovery(
    config: dict[str, Any], menuai: menuai, menuai_client: ClientSessionGenerator
) -> ClientResponse:
    """Submit a request to the Smart Home HTTP API."""
    await async_setup_component(menuai, DOMAIN, config)
    http_client = await menuai_client()

    request = get_new_request("Alexa.Discovery", "Discover")
    return await http_client.post(
        smart_home.SMART_HOME_HTTP_ENDPOINT,
        data=json.dumps(request),
        headers={"content-type": CONTENT_TYPE_JSON},
    )


@pytest.mark.parametrize(
    "config",
    [
        {"alexa": {"smart_home": None}},
        {
            "alexa": {
                "smart_home": {
                    "client_id": "someclientid",
                    "client_secret": "verysecret",
                }
            }
        },
    ],
)
async def test_http_api(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    menuai_client: ClientSessionGenerator,
    config: dict[str, Any],
) -> None:
    """With `smart_home:` HTTP API is exposed and debug log is redacted."""
    with caplog.at_level(logging.DEBUG):
        response = await do_http_discovery(config, menuai, menuai_client)
        response_data = await response.json()
        assert "'correlationToken': '**REDACTED**'" in caplog.text

    # Here we're testing just the HTTP view glue -- details of discovery are
    # covered in other tests.
    assert response_data["event"]["header"]["name"] == "Discover.Response"


async def test_http_api_disabled(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Without `smart_home:`, the HTTP API is disabled."""
    config = {"alexa": {}}
    response = await do_http_discovery(config, menuai, menuai_client)
    assert response.status == HTTPStatus.NOT_FOUND
