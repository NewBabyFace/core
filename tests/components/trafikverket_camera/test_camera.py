"""The test for the Trafikverket camera platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytrafikverket import CameraInfoModel

from menuai.components.camera import async_get_image
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import menuaiError

from tests.common import async_fire_time_changed
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_camera(
    menuai: menuai,
    load_int: ConfigEntry,
    freezer: FrozenDateTimeFactory,
    monkeypatch: pytest.MonkeyPatch,
    aioclient_mock: AiohttpClientMocker,
    get_camera: CameraInfoModel,
) -> None:
    """Test the Trafikverket Camera sensor."""
    state1 = menuai.states.get("camera.test_camera")
    assert state1.state == "idle"
    assert state1.attributes["description"] == "Test Camera for testing"
    assert state1.attributes["location"] == "Test location"
    assert state1.attributes["type"] == "Road"

    with patch(
        "menuai.components.trafikverket_camera.coordinator.TrafikverketCamera.async_get_camera",
        return_value=get_camera,
    ):
        aioclient_mock.get(
            "https://www.testurl.com/test_photo.jpg?type=fullsize",
            content=b"9876543210",
        )
        freezer.tick(timedelta(minutes=6))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    state1 = menuai.states.get("camera.test_camera")
    assert state1.state == "idle"
    assert state1.attributes != {}

    assert await async_get_image(menuai, "camera.test_camera")

    monkeypatch.setattr(
        get_camera,
        "photourl",
        None,
    )
    aioclient_mock.get(
        "https://www.testurl.com/test_photo.jpg?type=fullsize",
        status=404,
    )

    with patch(
        "menuai.components.trafikverket_camera.coordinator.TrafikverketCamera.async_get_camera",
        return_value=get_camera,
    ):
        freezer.tick(timedelta(minutes=6))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    with pytest.raises(menuaiError):
        await async_get_image(menuai, "camera.test_camera")
