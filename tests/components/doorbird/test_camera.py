"""Test DoorBird cameras."""

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.camera import (
    CameraState,
    async_get_image,
    async_get_stream_source,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError

from . import mock_not_found_exception
from .conftest import DoorbirdMockerType


async def test_doorbird_cameras(
    menuai: menuai,
    doorbird_mocker: DoorbirdMockerType,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the doorbird cameras."""
    doorbird_entry = await doorbird_mocker()
    live_camera_entity_id = "camera.mydoorbird_live"
    assert menuai.states.get(live_camera_entity_id).state == CameraState.IDLE
    last_motion_camera_entity_id = "camera.mydoorbird_last_motion"
    assert menuai.states.get(last_motion_camera_entity_id).state == CameraState.IDLE
    last_ring_camera_entity_id = "camera.mydoorbird_last_ring"
    assert menuai.states.get(last_ring_camera_entity_id).state == CameraState.IDLE
    assert await async_get_stream_source(menuai, live_camera_entity_id) is not None
    api = doorbird_entry.api
    api.get_image.side_effect = mock_not_found_exception()
    with pytest.raises(menuaiError):
        await async_get_image(menuai, live_camera_entity_id)
    api.get_image.side_effect = TimeoutError()
    with pytest.raises(menuaiError):
        await async_get_image(menuai, live_camera_entity_id)
    api.get_image.side_effect = None
    assert (await async_get_image(menuai, live_camera_entity_id)).content == b"image"
    api.get_image.return_value = b"notyet"
    # Ensure rate limit works
    assert (await async_get_image(menuai, live_camera_entity_id)).content == b"image"

    freezer.tick(60)
    assert (await async_get_image(menuai, live_camera_entity_id)).content == b"notyet"
