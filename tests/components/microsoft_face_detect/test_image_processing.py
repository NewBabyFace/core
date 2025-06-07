"""The tests for the microsoft face detect platform."""

from unittest.mock import PropertyMock, patch

import pytest

from menuai.components.image_processing import DOMAIN as IP_DOMAIN
from menuai.components.microsoft_face import DOMAIN as MF_DOMAIN, FACE_API_URL
from menuai.const import ATTR_ENTITY_PICTURE
from menuai.core import menuai, callback
from menuai.setup import async_setup_component

from tests.common import assert_setup_component, async_load_fixture
from tests.components.image_processing import common
from tests.test_util.aiohttp import AiohttpClientMocker

CONFIG = {
    IP_DOMAIN: {
        "platform": "microsoft_face_detect",
        "source": {"entity_id": "camera.demo_camera", "name": "test local"},
        "attributes": ["age", "gender"],
    },
    "camera": {"platform": "demo"},
    MF_DOMAIN: {"api_key": "12345678abcdef6"},
}

ENDPOINT_URL = f"https://westus.{FACE_API_URL}"


@pytest.fixture(autouse=True)
async def setup_menuai(menuai: menuai):
    """Set up the menuai integration."""
    await async_setup_component(menuai, "menuai", {})


@pytest.fixture
def store_mock():
    """Mock update store."""
    with patch(
        "menuai.components.microsoft_face.MicrosoftFace.update_store",
        return_value=None,
    ) as mock_update_store:
        yield mock_update_store


@pytest.fixture
def poll_mock():
    """Disable polling."""
    with patch(
        "menuai.components.microsoft_face_detect.image_processing."
        "MicrosoftFaceDetectEntity.should_poll",
        new_callable=PropertyMock(return_value=False),
    ):
        yield


async def test_setup_platform(menuai: menuai, store_mock) -> None:
    """Set up platform with one entity."""
    config = {
        IP_DOMAIN: {
            "platform": "microsoft_face_detect",
            "source": {"entity_id": "camera.demo_camera"},
            "attributes": ["age", "gender"],
        },
        "camera": {"platform": "demo"},
        MF_DOMAIN: {"api_key": "12345678abcdef6"},
    }

    with assert_setup_component(1, IP_DOMAIN):
        await async_setup_component(menuai, IP_DOMAIN, config)
        await menuai.async_block_till_done()

    assert menuai.states.get("image_processing.microsoftface_demo_camera")


async def test_setup_platform_name(menuai: menuai, store_mock) -> None:
    """Set up platform with one entity and set name."""
    config = {
        IP_DOMAIN: {
            "platform": "microsoft_face_detect",
            "source": {"entity_id": "camera.demo_camera", "name": "test local"},
        },
        "camera": {"platform": "demo"},
        MF_DOMAIN: {"api_key": "12345678abcdef6"},
    }

    with assert_setup_component(1, IP_DOMAIN):
        await async_setup_component(menuai, IP_DOMAIN, config)
        await menuai.async_block_till_done()

    assert menuai.states.get("image_processing.test_local")


async def test_ms_detect_process_image(
    menuai: menuai, poll_mock, aioclient_mock: AiohttpClientMocker
) -> None:
    """Set up and scan a picture and test plates from event."""
    aioclient_mock.get(
        ENDPOINT_URL.format("persongroups"),
        text=await async_load_fixture(
            menuai, "persongroups.json", "microsoft_face_detect"
        ),
    )
    aioclient_mock.get(
        ENDPOINT_URL.format("persongroups/test_group1/persons"),
        text=await async_load_fixture(menuai, "persons.json", "microsoft_face_detect"),
    )
    aioclient_mock.get(
        ENDPOINT_URL.format("persongroups/test_group2/persons"),
        text=await async_load_fixture(menuai, "persons.json", "microsoft_face_detect"),
    )

    await async_setup_component(menuai, IP_DOMAIN, CONFIG)
    await menuai.async_block_till_done()

    state = menuai.states.get("camera.demo_camera")
    url = f"{menuai.config.internal_url}{state.attributes.get(ATTR_ENTITY_PICTURE)}"

    face_events = []

    @callback
    def mock_face_event(event):
        """Mock event."""
        face_events.append(event)

    menuai.bus.async_listen("image_processing.detect_face", mock_face_event)

    aioclient_mock.get(url, content=b"image")

    aioclient_mock.post(
        ENDPOINT_URL.format("detect"),
        text=await async_load_fixture(menuai, "detect.json", "microsoft_face_detect"),
        params={"returnFaceAttributes": "age,gender"},
    )

    common.async_scan(menuai, entity_id="image_processing.test_local")
    await menuai.async_block_till_done()

    state = menuai.states.get("image_processing.test_local")

    assert len(face_events) == 1
    assert state.attributes.get("total_faces") == 1
    assert state.state == "1"

    assert face_events[0].data["age"] == 71.0
    assert face_events[0].data["gender"] == "male"
    assert face_events[0].data["entity_id"] == "image_processing.test_local"

    # Test that later, if a request is made that results in no face
    # being detected, that this is reflected in the state object
    aioclient_mock.clear_requests()
    aioclient_mock.post(
        ENDPOINT_URL.format("detect"),
        text="[]",
        params={"returnFaceAttributes": "age,gender"},
    )

    common.async_scan(menuai, entity_id="image_processing.test_local")
    await menuai.async_block_till_done()

    state = menuai.states.get("image_processing.test_local")

    # No more face events were fired
    assert len(face_events) == 1
    # Total faces and actual qualified number of faces reset to zero
    assert state.attributes.get("total_faces") == 0
    assert state.state == "0"
