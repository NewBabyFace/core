"""The tests for http static files."""

from http import HTTPStatus
from pathlib import Path

from aiohttp.test_utils import TestClient
import pytest

from menuai.components.http import StaticPathConfig
from menuai.components.http.static import CachingStaticResource
from menuai.const import EVENT_menuai_START
from menuai.core import menuai
from menuai.helpers.http import KEY_ALLOW_CONFIGURED_CORS
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True)
async def http(menuai: menuai) -> None:
    """Ensure http is set up."""
    assert await async_setup_component(menuai, "http", {})
    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()


@pytest.fixture
async def mock_http_client(menuai: menuai, aiohttp_client: ClientSessionGenerator):
    """Start the MenuAI HTTP component."""
    return await aiohttp_client(menuai.http.app, server_kwargs={"skip_url_asserts": True})


async def test_static_resource_show_index(
    menuai: menuai, mock_http_client: TestClient, tmp_path: Path
) -> None:
    """Test static resource will return a directory index."""
    app = menuai.http.app

    resource = CachingStaticResource("/", tmp_path, show_index=True)
    app.router.register_resource(resource)
    app[KEY_ALLOW_CONFIGURED_CORS](resource)

    resp = await mock_http_client.get("/")
    assert resp.status == 200
    assert resp.content_type == "text/html"


async def test_async_register_static_paths(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test registering multiple static paths."""
    assert await async_setup_component(menuai, "frontend", {})
    path = str(Path(__file__).parent)
    await menuai.http.async_register_static_paths(
        [
            StaticPathConfig("/something", path),
            StaticPathConfig("/something_else", path),
        ]
    )

    client = await menuai_client()
    resp = await client.get("/something/__init__.py")
    assert resp.status == HTTPStatus.OK
    resp = await client.get("/something_else/__init__.py")
    assert resp.status == HTTPStatus.OK
