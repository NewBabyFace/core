"""Test camera media source."""

from unittest.mock import PropertyMock, patch

import pytest

from menuai.components import media_source
from menuai.components.camera import CameraCapabilities
from menuai.components.camera.const import StreamType
from menuai.components.stream import FORMAT_CONTENT_TYPE
from menuai.core import menuai
from menuai.setup import async_setup_component


@pytest.fixture(autouse=True)
async def setup_media_source(menuai: menuai) -> None:
    """Set up media source."""
    assert await async_setup_component(menuai, "media_source", {})


@pytest.mark.usefixtures("mock_camera_with_device", "mock_camera")
async def test_device_with_device(menuai: menuai) -> None:
    """Test browsing when camera has a device and a name."""
    item = await media_source.async_browse_media(menuai, "media-source://camera")
    assert item.not_shown == 2
    assert len(item.children) == 1
    assert item.children[0].title == "Test Camera Device Demo camera without stream"


@pytest.mark.usefixtures("mock_camera_with_no_name", "mock_camera")
async def test_device_with_no_name(menuai: menuai) -> None:
    """Test browsing when camera has device and name == None."""
    item = await media_source.async_browse_media(menuai, "media-source://camera")
    assert item.not_shown == 2
    assert len(item.children) == 1
    assert item.children[0].title == "Test Camera Device Demo camera without stream"


@pytest.mark.usefixtures("mock_camera_hls")
async def test_browsing_hls(menuai: menuai) -> None:
    """Test browsing HLS camera media source."""
    item = await media_source.async_browse_media(menuai, "media-source://camera")
    assert item is not None
    assert item.title == "Camera"
    assert len(item.children) == 0
    assert item.not_shown == 3

    # Adding stream enables HLS camera
    menuai.config.components.add("stream")

    item = await media_source.async_browse_media(menuai, "media-source://camera")
    assert item.not_shown == 0
    assert len(item.children) == 3
    assert item.children[0].media_content_type == FORMAT_CONTENT_TYPE["hls"]


@pytest.mark.usefixtures("mock_camera")
async def test_browsing_mjpeg(menuai: menuai) -> None:
    """Test browsing MJPEG camera media source."""
    item = await media_source.async_browse_media(menuai, "media-source://camera")
    assert item is not None
    assert item.title == "Camera"
    assert len(item.children) == 1
    assert item.not_shown == 2
    assert item.children[0].media_content_type == "image/jpg"
    assert item.children[0].title == "Demo camera without stream"


@pytest.mark.usefixtures("mock_camera_webrtc")
async def test_browsing_webrtc(menuai: menuai) -> None:
    """Test browsing WebRTC camera media source."""
    # 3 cameras:
    # one only supports WebRTC (no stream source)
    # one raises when getting the source
    # One has a stream source, and should be the only browsable one
    with patch(
        "menuai.components.camera.Camera.stream_source",
        side_effect=["test", None, Exception],
    ):
        item = await media_source.async_browse_media(menuai, "media-source://camera")
        assert item is not None
        assert item.title == "Camera"
        assert len(item.children) == 0
        assert item.not_shown == 3

        # Adding stream enables HLS camera
        menuai.config.components.add("stream")

        item = await media_source.async_browse_media(menuai, "media-source://camera")
        assert item.not_shown == 2
        assert len(item.children) == 1
        assert item.children[0].media_content_type == FORMAT_CONTENT_TYPE["hls"]


@pytest.mark.usefixtures("mock_camera")
async def test_resolving(menuai: menuai) -> None:
    """Test resolving."""
    # Adding stream enables HLS camera
    menuai.config.components.add("stream")

    with patch(
        "menuai.components.camera.media_source._async_stream_endpoint_url",
        return_value="http://example.com/stream",
    ):
        item = await media_source.async_resolve_media(
            menuai, "media-source://camera/camera.demo_camera", None
        )
    assert item is not None
    assert item.url == "http://example.com/stream"
    assert item.mime_type == FORMAT_CONTENT_TYPE["hls"]


@pytest.mark.usefixtures("mock_camera")
async def test_resolving_errors(menuai: menuai) -> None:
    """Test resolving."""

    with pytest.raises(media_source.Unresolvable) as exc_info:
        await media_source.async_resolve_media(
            menuai, "media-source://camera/camera.demo_camera", None
        )
    assert str(exc_info.value) == "Stream integration not loaded"

    menuai.config.components.add("stream")

    with pytest.raises(media_source.Unresolvable) as exc_info:
        await media_source.async_resolve_media(
            menuai, "media-source://camera/camera.non_existing", None
        )
    assert str(exc_info.value) == "Could not resolve media item: camera.non_existing"

    with (
        pytest.raises(media_source.Unresolvable) as exc_info,
        patch(
            "menuai.components.camera.Camera.camera_capabilities",
            new_callable=PropertyMock(
                return_value=CameraCapabilities({StreamType.WEB_RTC})
            ),
        ),
    ):
        await media_source.async_resolve_media(
            menuai, "media-source://camera/camera.demo_camera", None
        )
    assert str(exc_info.value) == "Camera does not support MJPEG or HLS streaming."

    with pytest.raises(media_source.Unresolvable) as exc_info:
        await media_source.async_resolve_media(
            menuai, "media-source://camera/camera.demo_camera", None
        )
    assert (
        str(exc_info.value) == "camera.demo_camera does not support play stream service"
    )
