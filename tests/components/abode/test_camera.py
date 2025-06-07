"""Tests for the Abode camera device."""

from unittest.mock import patch

from menuai.components.abode.const import DOMAIN
from menuai.components.camera import DOMAIN as CAMERA_DOMAIN, CameraState
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import setup_platform


async def test_entity_registry(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(menuai, CAMERA_DOMAIN)

    entry = entity_registry.async_get("camera.test_cam")
    assert entry.unique_id == "d0a3a1c316891ceb00c20118aae2a133"


async def test_attributes(menuai: menuai) -> None:
    """Test the camera attributes are correct."""
    await setup_platform(menuai, CAMERA_DOMAIN)

    state = menuai.states.get("camera.test_cam")
    assert state.state == CameraState.IDLE


async def test_capture_image(menuai: menuai) -> None:
    """Test the camera capture image service."""
    await setup_platform(menuai, CAMERA_DOMAIN)

    with patch("jaraco.abode.devices.camera.Camera.capture") as mock_capture:
        await menuai.services.async_call(
            DOMAIN,
            "capture_image",
            {ATTR_ENTITY_ID: "camera.test_cam"},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_capture.assert_called_once()


async def test_camera_on(menuai: menuai) -> None:
    """Test the camera turn on service."""
    await setup_platform(menuai, CAMERA_DOMAIN)

    with patch("jaraco.abode.devices.camera.Camera.privacy_mode") as mock_capture:
        await menuai.services.async_call(
            CAMERA_DOMAIN,
            "turn_on",
            {ATTR_ENTITY_ID: "camera.test_cam"},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_capture.assert_called_once_with(False)


async def test_camera_off(menuai: menuai) -> None:
    """Test the camera turn off service."""
    await setup_platform(menuai, CAMERA_DOMAIN)

    with patch("jaraco.abode.devices.camera.Camera.privacy_mode") as mock_capture:
        await menuai.services.async_call(
            CAMERA_DOMAIN,
            "turn_off",
            {ATTR_ENTITY_ID: "camera.test_cam"},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_capture.assert_called_once_with(True)
