"""The tests for the Template image platform."""

from http import HTTPStatus
from io import BytesIO
from typing import Any

import httpx
from PIL import Image
import pytest
import respx
from syrupy.assertion import SnapshotAssertion

from menuai import setup
from menuai.components.input_text import (
    ATTR_VALUE as INPUT_TEXT_ATTR_VALUE,
    DOMAIN as INPUT_TEXT_DOMAIN,
    SERVICE_SET_VALUE as INPUT_TEXT_SERVICE_SET_VALUE,
)
from menuai.components.template import DOMAIN
from menuai.const import ATTR_ENTITY_PICTURE, CONF_ENTITY_ID, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry, assert_setup_component
from tests.typing import ClientSessionGenerator

_DEFAULT = object()
_TEST_IMAGE = "image.template_image"
_URL_INPUT_TEXT = "input_text.url"


@pytest.fixture
def imgbytes_jpg():
    """Image in RAM for testing."""
    buf = BytesIO()  # fake image in ram for testing.
    Image.new("RGB", (1, 1)).save(buf, format="jpeg")
    return bytes(buf.getbuffer())


@pytest.fixture
def imgbytes2_jpg():
    """Image in RAM for testing."""
    buf = BytesIO()  # fake image in ram for testing.
    Image.new("RGB", (1, 1), 100).save(buf, format="jpeg")
    return bytes(buf.getbuffer())


async def _assert_state(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    expected_state: str,
    expected_image: bytes | None,
    entity_id: str = _TEST_IMAGE,
    expected_content_type: str = "image/jpeg",
    expected_entity_picture: Any = _DEFAULT,
    expected_status: HTTPStatus = HTTPStatus.OK,
):
    """Verify image's state."""
    state = menuai.states.get(entity_id)
    attributes = state.attributes
    assert state.state == expected_state
    if expected_entity_picture is _DEFAULT:
        expected_entity_picture = (
            f"/api/image_proxy/{entity_id}?token={attributes['access_token']}"
        )

    assert attributes.get(ATTR_ENTITY_PICTURE) == expected_entity_picture

    client = await menuai_client()

    resp = await client.get(f"/api/image_proxy/{entity_id}")
    assert resp.content_type == expected_content_type
    assert resp.status == expected_status
    body = await resp.read()
    assert body == expected_image


@respx.mock
@pytest.mark.freeze_time("2024-07-09 00:00:00+00:00")
async def test_setup_config_entry(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    imgbytes_jpg,
) -> None:
    """Test the config flow."""

    respx.get("http://example.com").respond(
        stream=imgbytes_jpg, content_type="image/jpeg"
    )

    template_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": "My template",
            "template_type": "image",
            "url": "http://example.com",
        },
        title="My template",
    )
    template_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(template_config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("image.my_template")
    assert state is not None
    assert state.state == "2024-07-09T00:00:00+00:00"


@respx.mock
@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_platform_config(
    menuai: menuai, menuai_client: ClientSessionGenerator, imgbytes_jpg
) -> None:
    """Test configuring under the platform key does not work."""
    respx.get("http://example.com").respond(
        stream=imgbytes_jpg, content_type="image/jpeg"
    )

    with assert_setup_component(1, "image"):
        assert await setup.async_setup_component(
            menuai,
            "image",
            {
                "image": {
                    "platform": "template",
                    "url": "{{ 'http://example.com' }}",
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0


@respx.mock
@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_missing_optional_config(
    menuai: menuai, menuai_client: ClientSessionGenerator, imgbytes_jpg
) -> None:
    """Test: missing optional template is ok."""
    respx.get("http://example.com").respond(
        stream=imgbytes_jpg, content_type="image/jpeg"
    )

    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "image": {
                        "url": "{{ 'http://example.com' }}",
                    }
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    expected_state = dt_util.utcnow().isoformat()
    await _assert_state(menuai, menuai_client, expected_state, imgbytes_jpg)
    assert respx.get("http://example.com").call_count == 1

    # Check the image is not refetched
    await _assert_state(menuai, menuai_client, expected_state, imgbytes_jpg)
    assert respx.get("http://example.com").call_count == 1


@respx.mock
@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_multiple_configs(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    imgbytes_jpg,
    imgbytes2_jpg,
) -> None:
    """Test: multiple image entities get created."""
    respx.get("http://example.com").respond(
        stream=imgbytes_jpg, content_type="image/jpeg"
    )
    respx.get("http://example2.com").respond(
        stream=imgbytes2_jpg, content_type="image/png"
    )

    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "image": [
                        {
                            "url": "{{ 'http://example.com' }}",
                        },
                        {
                            "url": "{{ 'http://example2.com' }}",
                        },
                    ]
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    expected_state = dt_util.utcnow().isoformat()
    await _assert_state(menuai, menuai_client, expected_state, imgbytes_jpg)
    await _assert_state(
        menuai,
        menuai_client,
        expected_state,
        imgbytes2_jpg,
        f"{_TEST_IMAGE}_2",
        expected_content_type="image/png",
    )


async def test_missing_required_keys(menuai: menuai) -> None:
    """Test: missing required fields will fail."""
    with assert_setup_component(0, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "image": {
                        "name": "a name",
                    }
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    assert menuai.states.async_all("image") == []


async def test_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test unique_id configuration."""
    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "unique_id": "b",
                    "image": {
                        "url": "http://example.com",
                        "unique_id": "a",
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    entry = entity_registry.async_get(_TEST_IMAGE)
    assert entry
    assert entry.unique_id == "b-a"


@respx.mock
@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_custom_entity_picture(
    menuai: menuai, menuai_client: ClientSessionGenerator, imgbytes_jpg
) -> None:
    """Test custom entity picture."""
    respx.get("http://example.com").respond(
        stream=imgbytes_jpg, content_type="image/jpeg"
    )

    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "image": {
                        "url": "http://example.com",
                        "picture": "http://example2.com",
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    expected_state = dt_util.utcnow().isoformat()
    await _assert_state(
        menuai,
        menuai_client,
        expected_state,
        imgbytes_jpg,
        expected_entity_picture="http://example2.com",
    )


@respx.mock
async def test_template_error(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test handling template error."""
    respx.get("http://example.com").side_effect = httpx.TimeoutException

    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "image": {
                        "url": "{{ no_such_variable.url }}",
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    await _assert_state(
        menuai,
        menuai_client,
        STATE_UNKNOWN,
        b"500: Internal Server Error",
        expected_status=HTTPStatus.INTERNAL_SERVER_ERROR,
        expected_content_type="text/plain",
    )


@respx.mock
@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_templates_with_entities(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    imgbytes_jpg,
    imgbytes2_jpg,
) -> None:
    """Test templates with values from other entities."""
    respx.get("http://example.com").respond(
        stream=imgbytes_jpg, content_type="image/jpeg"
    )
    respx.get("http://example2.com").respond(
        stream=imgbytes2_jpg, content_type="image/png"
    )

    with assert_setup_component(1, "input_text"):
        assert await setup.async_setup_component(
            menuai,
            "input_text",
            {
                "input_text": {
                    "url": {
                        "initial": "http://example.com",
                        "name": "url",
                    },
                }
            },
        )

    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "image": {
                        "url": f"{{{{ states('{_URL_INPUT_TEXT}') }}}}",
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    expected_state = dt_util.utcnow().isoformat()
    await _assert_state(menuai, menuai_client, expected_state, imgbytes_jpg)
    assert respx.get("http://example.com").call_count == 1

    # Check the image is not refetched
    await _assert_state(menuai, menuai_client, expected_state, imgbytes_jpg)
    assert respx.get("http://example.com").call_count == 1

    await menuai.services.async_call(
        INPUT_TEXT_DOMAIN,
        INPUT_TEXT_SERVICE_SET_VALUE,
        {CONF_ENTITY_ID: _URL_INPUT_TEXT, INPUT_TEXT_ATTR_VALUE: "http://example2.com"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    await _assert_state(
        menuai,
        menuai_client,
        expected_state,
        imgbytes2_jpg,
        expected_content_type="image/png",
    )


@respx.mock
@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_trigger_image(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    imgbytes_jpg,
    imgbytes2_jpg,
) -> None:
    """Test trigger based template image."""
    respx.get("http://example.com").respond(
        stream=imgbytes_jpg, content_type="image/jpeg"
    )
    respx.get("http://example2.com").respond(
        stream=imgbytes2_jpg, content_type="image/png"
    )

    assert await setup.async_setup_component(
        menuai,
        "template",
        {
            "template": [
                {
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "image": [
                        {
                            "url": "{{ trigger.event.data.url }}",
                        },
                    ],
                },
            ],
        },
    )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    # No image is loaded, expect error
    await _assert_state(
        menuai,
        menuai_client,
        "unknown",
        b"500: Internal Server Error",
        expected_status=HTTPStatus.INTERNAL_SERVER_ERROR,
        expected_content_type="text/plain",
    )

    menuai.bus.async_fire("test_event", {"url": "http://example.com"})
    await menuai.async_block_till_done()
    expected_state = dt_util.utcnow().isoformat()
    await _assert_state(menuai, menuai_client, expected_state, imgbytes_jpg)
    assert respx.get("http://example.com").call_count == 1

    # Check the image is not refetched
    await _assert_state(menuai, menuai_client, expected_state, imgbytes_jpg)
    assert respx.get("http://example.com").call_count == 1

    menuai.bus.async_fire("test_event", {"url": "http://example2.com"})
    await menuai.async_block_till_done()
    await _assert_state(
        menuai,
        menuai_client,
        expected_state,
        imgbytes2_jpg,
        expected_content_type="image/png",
    )


@respx.mock
@pytest.mark.freeze_time("2023-04-01 00:00:00+00:00")
async def test_trigger_image_custom_entity_picture(
    menuai: menuai, menuai_client: ClientSessionGenerator, imgbytes_jpg
) -> None:
    """Test trigger based template image with custom entity picture."""
    respx.get("http://example.com").respond(
        stream=imgbytes_jpg, content_type="image/jpeg"
    )

    assert await setup.async_setup_component(
        menuai,
        "template",
        {
            "template": [
                {
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "image": [
                        {
                            "url": "{{ trigger.event.data.url }}",
                            "picture": "http://example2.com",
                        },
                    ],
                },
            ],
        },
    )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    # No image is loaded, expect error
    await _assert_state(
        menuai,
        menuai_client,
        "unknown",
        b"500: Internal Server Error",
        expected_status=HTTPStatus.INTERNAL_SERVER_ERROR,
        expected_entity_picture="http://example2.com",
        expected_content_type="text/plain",
    )

    menuai.bus.async_fire("test_event", {"url": "http://example.com"})
    await menuai.async_block_till_done()
    expected_state = dt_util.utcnow().isoformat()
    await _assert_state(
        menuai,
        menuai_client,
        expected_state,
        imgbytes_jpg,
        expected_entity_picture="http://example2.com",
    )


@respx.mock
async def test_device_id(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for device for image template."""

    device_config_entry = MockConfigEntry()
    device_config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=device_config_entry.entry_id,
        identifiers={("test", "identifier_test")},
        connections={("mac", "30:31:32:33:34:35")},
    )
    await menuai.async_block_till_done()
    assert device_entry is not None
    assert device_entry.id is not None

    respx.get("http://example.com").respond(
        stream=imgbytes_jpg, content_type="image/jpeg"
    )

    template_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": "My template",
            "template_type": "image",
            "url": "http://example.com",
            "device_id": device_entry.id,
        },
        title="My template",
    )
    template_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(template_config_entry.entry_id)
    await menuai.async_block_till_done()

    template_entity = entity_registry.async_get("image.my_template")
    assert template_entity is not None
    assert template_entity.device_id == device_entry.id
