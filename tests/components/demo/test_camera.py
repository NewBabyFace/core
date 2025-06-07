"""The tests for local file camera component."""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from menuai.components.camera import (
    DOMAIN as CAMERA_DOMAIN,
    SERVICE_DISABLE_MOTION,
    SERVICE_ENABLE_MOTION,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    CameraState,
    async_get_image,
)
from menuai.components.demo import DOMAIN
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.setup import async_setup_component

ENTITY_CAMERA = "camera.demo_camera"


@pytest.fixture
def camera_only() -> Generator[None]:
    """Enable only the button platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.CAMERA],
    ):
        yield


@pytest.fixture(autouse=True)
async def demo_camera(menuai: menuai, camera_only: None) -> None:
    """Initialize a demo camera platform."""
    assert await async_setup_component(
        menuai, CAMERA_DOMAIN, {CAMERA_DOMAIN: {"platform": DOMAIN}}
    )
    await menuai.async_block_till_done()


async def test_init_state_is_streaming(menuai: menuai) -> None:
    """Demo camera initialize as streaming."""
    state = menuai.states.get(ENTITY_CAMERA)
    assert state.state == CameraState.STREAMING

    with patch(
        "menuai.components.demo.camera.Path.read_bytes", return_value=b"ON"
    ) as mock_read_bytes:
        image = await async_get_image(menuai, ENTITY_CAMERA)
        assert mock_read_bytes.call_count == 1
        assert image.content == b"ON"


async def test_turn_on_state_back_to_streaming(menuai: menuai) -> None:
    """After turn on state back to streaming."""
    state = menuai.states.get(ENTITY_CAMERA)
    assert state.state == CameraState.STREAMING

    await menuai.services.async_call(
        CAMERA_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_CAMERA}, blocking=True
    )

    state = menuai.states.get(ENTITY_CAMERA)
    assert state.state == CameraState.IDLE

    await menuai.services.async_call(
        CAMERA_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_CAMERA}, blocking=True
    )

    state = menuai.states.get(ENTITY_CAMERA)
    assert state.state == CameraState.STREAMING


async def test_turn_off_image(menuai: menuai) -> None:
    """After turn off, Demo camera raise error."""
    await menuai.services.async_call(
        CAMERA_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_CAMERA}, blocking=True
    )

    with pytest.raises(menuaiError) as error:
        await async_get_image(menuai, ENTITY_CAMERA)
    assert error.value.args[0] == "Camera is off"


async def test_turn_off_invalid_camera(menuai: menuai) -> None:
    """Turn off non-exist camera should quietly fail."""
    state = menuai.states.get(ENTITY_CAMERA)
    assert state.state == CameraState.STREAMING

    await menuai.services.async_call(
        CAMERA_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "camera.invalid_camera"},
        blocking=True,
    )

    state = menuai.states.get(ENTITY_CAMERA)
    assert state.state == CameraState.STREAMING


async def test_motion_detection(menuai: menuai) -> None:
    """Test motion detection services."""

    # Fetch state and check motion detection attribute
    state = menuai.states.get(ENTITY_CAMERA)
    assert not state.attributes.get("motion_detection")

    # Call service to turn on motion detection
    await menuai.services.async_call(
        CAMERA_DOMAIN,
        SERVICE_ENABLE_MOTION,
        {ATTR_ENTITY_ID: ENTITY_CAMERA},
        blocking=True,
    )

    # Check if state has been updated.
    state = menuai.states.get(ENTITY_CAMERA)
    assert state.attributes.get("motion_detection")

    # Call service to turn off motion detection
    await menuai.services.async_call(
        CAMERA_DOMAIN,
        SERVICE_DISABLE_MOTION,
        {ATTR_ENTITY_ID: ENTITY_CAMERA},
        blocking=True,
    )

    # Check if state has been updated.
    state = menuai.states.get(ENTITY_CAMERA)
    assert not state.attributes.get("motion_detection")
