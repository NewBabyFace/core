"""The tests for the image component."""

from datetime import datetime
from http import HTTPStatus
import ssl
from unittest.mock import MagicMock, mock_open, patch

from aiohttp import hdrs
from freezegun.api import FrozenDateTimeFactory
import httpx
import pytest
import respx

from menuai.components import image
from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.setup import async_setup_component

from .conftest import (
    MockImageEntity,
    MockImageEntityCapitalContentType,
    MockImageEntityInvalidContentType,
    MockImageNoDataEntity,
    MockImageNoStateEntity,
    MockImagePlatform,
    MockImageSyncEntity,
    MockURLImageEntity,
)

from tests.common import (
    MockModule,
    async_fire_time_changed,
    mock_integration,
    mock_platform,
)
from tests.typing import ClientSessionGenerator


@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_state(
    menuai: menuai, menuai_client: ClientSessionGenerator, mock_image_platform: None
) -> None:
    """Test image state."""
    state = menuai.states.get("image.test")
    assert state.state == "2023-04-01T00:00:00+00:00"
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": f"/api/image_proxy/image.test?token={access_token}",
        "friendly_name": "Test",
    }


@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_config_entry(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    mock_image_config_entry: ConfigEntry,
) -> None:
    """Test setting up an image platform from a config entry."""
    state = menuai.states.get("image.test")
    assert state.state == "2023-04-01T00:00:00+00:00"
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": f"/api/image_proxy/image.test?token={access_token}",
        "friendly_name": "Test",
    }


@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_state_attr(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test image state with entity picture from attr."""
    mock_integration(menuai, MockModule(domain="test"))
    entity = MockImageEntity(menuai)
    entity._attr_entity_picture = "abcd"
    mock_platform(menuai, "test.image", MockImagePlatform([entity]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("image.test")
    assert state.state == "2023-04-01T00:00:00+00:00"
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": "abcd",
        "friendly_name": "Test",
    }


async def test_no_state(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test image state."""
    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(menuai, "test.image", MockImagePlatform([MockImageNoStateEntity(menuai)]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("image.test")
    assert state.state == "unknown"
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": f"/api/image_proxy/image.test?token={access_token}",
        "friendly_name": "Test",
    }


async def test_no_valid_content_type(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test invalid content type."""
    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(
        menuai, "test.image", MockImagePlatform([MockImageEntityInvalidContentType(menuai)])
    )
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    client = await menuai_client()

    state = menuai.states.get("image.test")
    # assert state.state == "unknown"
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": f"/api/image_proxy/image.test?token={access_token}",
        "friendly_name": "Test",
    }
    resp = await client.get(f"/api/image_proxy/image.test?token={access_token}")
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_valid_but_capitalized_content_type(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test invalid content type."""
    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(
        menuai, "test.image", MockImagePlatform([MockImageEntityCapitalContentType(menuai)])
    )
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    client = await menuai_client()

    state = menuai.states.get("image.test")
    access_token = state.attributes["access_token"]
    assert state.attributes == {
        "access_token": access_token,
        "entity_picture": f"/api/image_proxy/image.test?token={access_token}",
        "friendly_name": "Test",
    }
    resp = await client.get(f"/api/image_proxy/image.test?token={access_token}")
    assert resp.status == HTTPStatus.OK


async def test_fetch_image_authenticated(
    menuai: menuai, menuai_client: ClientSessionGenerator, mock_image_platform: None
) -> None:
    """Test fetching an image with an authenticated client."""
    client = await menuai_client()

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == b"Test"

    resp = await client.get("/api/image_proxy/image.unknown")
    assert resp.status == HTTPStatus.NOT_FOUND


async def test_fetch_image_fail(
    menuai: menuai, menuai_client: ClientSessionGenerator, mock_image_platform: None
) -> None:
    """Test fetching an image with an authenticated client."""
    client = await menuai_client()

    with patch.object(MockImageEntity, "async_image", side_effect=TimeoutError):
        resp = await client.get("/api/image_proxy/image.test")
        assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_fetch_image_sync(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test fetching an image with an authenticated client."""
    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(menuai, "test.image", MockImagePlatform([MockImageSyncEntity(menuai)]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    client = await menuai_client()

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == b"Test"


async def test_fetch_image_unauthenticated(
    menuai: menuai,
    menuai_client_no_auth: ClientSessionGenerator,
    mock_image_platform: None,
) -> None:
    """Test fetching an image with an unauthenticated client."""
    client = await menuai_client_no_auth()

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.FORBIDDEN

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.FORBIDDEN

    resp = await client.get(
        "/api/image_proxy/image.test", headers={hdrs.AUTHORIZATION: "blabla"}
    )
    assert resp.status == HTTPStatus.UNAUTHORIZED

    state = menuai.states.get("image.test")
    resp = await client.get(state.attributes["entity_picture"])
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == b"Test"

    resp = await client.get("/api/image_proxy/image.unknown")
    assert resp.status == HTTPStatus.NOT_FOUND


@respx.mock
async def test_fetch_image_url_success(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test fetching an image with an authenticated client."""
    respx.get("https://example.com/myimage.jpg").respond(
        status_code=HTTPStatus.OK, content_type="image/png", content=b"Test"
    )

    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(menuai, "test.image", MockImagePlatform([MockURLImageEntity(menuai)]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    client = await menuai_client()

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == b"Test"


@respx.mock
@pytest.mark.parametrize(
    "side_effect",
    [
        httpx.RequestError("server offline", request=MagicMock()),
        httpx.TimeoutException,
        ssl.SSLError,
    ],
)
async def test_fetch_image_url_exception(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    side_effect: Exception,
) -> None:
    """Test fetching an image with an authenticated client."""
    respx.get("https://example.com/myimage.jpg").mock(side_effect=side_effect)

    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(menuai, "test.image", MockImagePlatform([MockURLImageEntity(menuai)]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    client = await menuai_client()

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


@respx.mock
@pytest.mark.parametrize(
    "content_type",
    [
        None,
        "text/plain",
    ],
)
async def test_fetch_image_url_wrong_content_type(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    content_type: str | None,
) -> None:
    """Test fetching an image with an authenticated client."""
    respx.get("https://example.com/myimage.jpg").respond(
        status_code=HTTPStatus.OK, content_type=content_type, content=b"Test"
    )

    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(menuai, "test.image", MockImagePlatform([MockURLImageEntity(menuai)]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    client = await menuai_client()

    resp = await client.get("/api/image_proxy/image.test")
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR


async def test_image_stream(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test image stream."""

    mock_integration(menuai, MockModule(domain="test"))
    mock_image = MockURLImageEntity(menuai)
    mock_platform(menuai, "test.image", MockImagePlatform([mock_image]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    client = await menuai_client()

    close_future = menuai.loop.create_future()
    original_get_still_stream = image.async_get_still_stream

    async def _wrap_async_get_still_stream(*args, **kwargs):
        result = await original_get_still_stream(*args, **kwargs)
        menuai.loop.call_soon(close_future.set_result, None)
        return result

    with patch(
        "menuai.components.image.async_get_still_stream",
        _wrap_async_get_still_stream,
    ):
        with patch.object(mock_image, "async_image", return_value=b""):
            resp = await client.get("/api/image_proxy_stream/image.test")
            assert not resp.closed
            assert resp.status == HTTPStatus.OK

            mock_image.image_last_updated = datetime.now()
            mock_image.async_write_ha_state()
            # Two blocks to ensure the frame is written
            await menuai.async_block_till_done()
            await menuai.async_block_till_done()

        with patch.object(mock_image, "async_image", return_value=b"") as mock:
            # Simulate a "keep alive" frame
            freezer.tick(55)
            async_fire_time_changed(menuai)
            # Two blocks to ensure the frame is written
            await menuai.async_block_till_done()
            await menuai.async_block_till_done()
            mock.assert_called_once()

        with patch.object(mock_image, "async_image", return_value=None):
            freezer.tick(55)
            async_fire_time_changed(menuai)
            # Two blocks to ensure the frame is written
            await menuai.async_block_till_done()
            await menuai.async_block_till_done()

    await close_future


async def test_snapshot_service(menuai: menuai) -> None:
    """Test snapshot service."""
    mopen = mock_open()
    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(menuai, "test.image", MockImagePlatform([MockImageSyncEntity(menuai)]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    with (
        patch("menuai.components.image.open", mopen, create=True),
        patch("menuai.components.image.os.makedirs"),
        patch.object(menuai.config, "is_allowed_path", return_value=True),
    ):
        await menuai.services.async_call(
            image.DOMAIN,
            image.SERVICE_SNAPSHOT,
            {
                ATTR_ENTITY_ID: "image.test",
                image.ATTR_FILENAME: "/test/snapshot.jpg",
            },
            blocking=True,
        )

        mock_write = mopen().write

        assert len(mock_write.mock_calls) == 1
        assert mock_write.mock_calls[0][1][0] == b"Test"


async def test_snapshot_service_no_image(menuai: menuai) -> None:
    """Test snapshot service with no image."""
    mopen = mock_open()
    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(menuai, "test.image", MockImagePlatform([MockImageNoDataEntity(menuai)]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    with (
        patch("menuai.components.image.open", mopen, create=True),
        patch(
            "menuai.components.image.os.makedirs",
        ),
        patch.object(menuai.config, "is_allowed_path", return_value=True),
    ):
        await menuai.services.async_call(
            image.DOMAIN,
            image.SERVICE_SNAPSHOT,
            {
                ATTR_ENTITY_ID: "image.test",
                image.ATTR_FILENAME: "/test/snapshot.jpg",
            },
            blocking=True,
        )

        mock_write = mopen().write

        assert len(mock_write.mock_calls) == 0


async def test_snapshot_service_not_allowed_path(menuai: menuai) -> None:
    """Test snapshot service with a not allowed path."""
    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(menuai, "test.image", MockImagePlatform([MockURLImageEntity(menuai)]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    with pytest.raises(menuaiError, match="/test/snapshot.jpg"):
        await menuai.services.async_call(
            image.DOMAIN,
            image.SERVICE_SNAPSHOT,
            {
                ATTR_ENTITY_ID: "image.test",
                image.ATTR_FILENAME: "/test/snapshot.jpg",
            },
            blocking=True,
        )


async def test_snapshot_service_os_error(menuai: menuai) -> None:
    """Test snapshot service with os error."""
    mock_integration(menuai, MockModule(domain="test"))
    mock_platform(menuai, "test.image", MockImagePlatform([MockImageSyncEntity(menuai)]))
    assert await async_setup_component(
        menuai, image.DOMAIN, {"image": {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    with (
        patch.object(menuai.config, "is_allowed_path", return_value=True),
        patch("os.makedirs", side_effect=OSError),
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            image.DOMAIN,
            image.SERVICE_SNAPSHOT,
            {
                ATTR_ENTITY_ID: "image.test",
                image.ATTR_FILENAME: "/test/snapshot.jpg",
            },
            blocking=True,
        )
