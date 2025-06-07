"""The tests for Octoptint camera module."""

from unittest.mock import patch

from pyoctoprintapi import WebcamSettings

from menuai.components.camera import DOMAIN as CAMERA_DOMAIN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration


async def test_camera(menuai: menuai, entity_registry: er.EntityRegistry) -> None:
    """Test the underlying camera."""
    with patch(
        "pyoctoprintapi.OctoprintClient.get_webcam_info",
        return_value=WebcamSettings(
            base_url="http://fake-octoprint/",
            raw={
                "streamUrl": "/webcam/?action=stream",
                "snapshotUrl": "http://127.0.0.1:8080/?action=snapshot",
                "webcamEnabled": True,
            },
        ),
    ):
        await init_integration(menuai, CAMERA_DOMAIN)

    entry = entity_registry.async_get("camera.octoprint_camera")
    assert entry is not None
    assert entry.unique_id == "uuid"


async def test_camera_disabled(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test that the camera does not load if there is not one configured."""
    with patch(
        "pyoctoprintapi.OctoprintClient.get_webcam_info",
        return_value=WebcamSettings(
            base_url="http://fake-octoprint/",
            raw={
                "streamUrl": "/webcam/?action=stream",
                "snapshotUrl": "http://127.0.0.1:8080/?action=snapshot",
                "webcamEnabled": False,
            },
        ),
    ):
        await init_integration(menuai, CAMERA_DOMAIN)

    entry = entity_registry.async_get("camera.octoprint_camera")
    assert entry is None


async def test_no_supported_camera(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test that the camera does not load if there is not one configured."""
    with patch(
        "pyoctoprintapi.OctoprintClient.get_webcam_info",
        return_value=None,
    ):
        await init_integration(menuai, CAMERA_DOMAIN)

    entry = entity_registry.async_get("camera.octoprint_camera")
    assert entry is None
