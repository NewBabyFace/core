"""The tests for MenuAI ffmpeg."""

from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

from menuai.components import ffmpeg
from menuai.components.ffmpeg import DOMAIN, get_ffmpeg_manager
from menuai.components.ffmpeg.services import (
    SERVICE_RESTART,
    SERVICE_START,
    SERVICE_STOP,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    EVENT_menuai_START,
    EVENT_menuai_STOP,
)
from menuai.core import menuai, callback
from menuai.setup import async_setup_component

from tests.common import assert_setup_component


@callback
def async_start(menuai: menuai, entity_id: str | None = None) -> None:
    """Start a FFmpeg process on entity.

    This is a legacy helper method. Do not use it for new tests.
    """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    menuai.async_create_task(menuai.services.async_call(DOMAIN, SERVICE_START, data))


@callback
def async_stop(menuai: menuai, entity_id: str | None = None) -> None:
    """Stop a FFmpeg process on entity.

    This is a legacy helper method. Do not use it for new tests.
    """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    menuai.async_create_task(menuai.services.async_call(DOMAIN, SERVICE_STOP, data))


@callback
def async_restart(menuai: menuai, entity_id: str | None = None) -> None:
    """Restart a FFmpeg process on entity.

    This is a legacy helper method. Do not use it for new tests.
    """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    menuai.async_create_task(menuai.services.async_call(DOMAIN, SERVICE_RESTART, data))


class MockFFmpegDev(ffmpeg.FFmpegBase):
    """FFmpeg device mock."""

    def __init__(
        self,
        menuai: menuai,
        initial_state: bool = True,
        entity_id: str = "test.ffmpeg_device",
    ) -> None:
        """Initialize mock."""
        super().__init__(None, initial_state)

        self.menuai = menuai
        self.entity_id = entity_id
        self.ffmpeg = MagicMock()
        self.called_stop = False
        self.called_start = False
        self.called_restart = False
        self.called_entities = None

    async def _async_start_ffmpeg(self, entity_ids):
        """Mock start."""
        self.called_start = True
        self.called_entities = entity_ids

    async def _async_stop_ffmpeg(self, entity_ids):
        """Mock stop."""
        self.called_stop = True
        self.called_entities = entity_ids


async def test_setup_component(menuai: menuai) -> None:
    """Set up ffmpeg component."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    assert menuai.data[ffmpeg.DATA_FFMPEG].binary == "ffmpeg"


async def test_setup_component_test_service(menuai: menuai) -> None:
    """Set up ffmpeg component test services."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    assert menuai.services.has_service(DOMAIN, "start")
    assert menuai.services.has_service(DOMAIN, "stop")
    assert menuai.services.has_service(DOMAIN, "restart")


async def test_setup_component_test_register(menuai: menuai) -> None:
    """Set up ffmpeg component test register."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    ffmpeg_dev = MockFFmpegDev(menuai)
    ffmpeg_dev._async_stop_ffmpeg = AsyncMock()
    ffmpeg_dev._async_start_ffmpeg = AsyncMock()
    await ffmpeg_dev.async_added_to_menuai()

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert len(ffmpeg_dev._async_start_ffmpeg.mock_calls) == 2

    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()
    assert len(ffmpeg_dev._async_stop_ffmpeg.mock_calls) == 2


async def test_setup_component_test_register_no_startup(menuai: menuai) -> None:
    """Set up ffmpeg component test register without startup."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    ffmpeg_dev = MockFFmpegDev(menuai, False)
    ffmpeg_dev._async_stop_ffmpeg = AsyncMock()
    ffmpeg_dev._async_start_ffmpeg = AsyncMock()
    await ffmpeg_dev.async_added_to_menuai()

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert len(ffmpeg_dev._async_start_ffmpeg.mock_calls) == 1

    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()
    assert len(ffmpeg_dev._async_stop_ffmpeg.mock_calls) == 2


async def test_setup_component_test_service_start(menuai: menuai) -> None:
    """Set up ffmpeg component test service start."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    ffmpeg_dev = MockFFmpegDev(menuai, False)
    await ffmpeg_dev.async_added_to_menuai()

    async_start(menuai)
    await menuai.async_block_till_done()

    assert ffmpeg_dev.called_start


async def test_setup_component_test_service_stop(menuai: menuai) -> None:
    """Set up ffmpeg component test service stop."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    ffmpeg_dev = MockFFmpegDev(menuai, False)
    await ffmpeg_dev.async_added_to_menuai()

    async_stop(menuai)
    await menuai.async_block_till_done()

    assert ffmpeg_dev.called_stop


async def test_setup_component_test_service_restart(menuai: menuai) -> None:
    """Set up ffmpeg component test service restart."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    ffmpeg_dev = MockFFmpegDev(menuai, False)
    await ffmpeg_dev.async_added_to_menuai()

    async_restart(menuai)
    await menuai.async_block_till_done()

    assert ffmpeg_dev.called_stop
    assert ffmpeg_dev.called_start


async def test_setup_component_test_service_start_with_entity(
    menuai: menuai,
) -> None:
    """Set up ffmpeg component test service start."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    ffmpeg_dev = MockFFmpegDev(menuai, False)
    await ffmpeg_dev.async_added_to_menuai()

    async_start(menuai, "test.ffmpeg_device")
    await menuai.async_block_till_done()

    assert ffmpeg_dev.called_start
    assert ffmpeg_dev.called_entities == ["test.ffmpeg_device"]


async def test_async_get_image_with_width_height(menuai: menuai) -> None:
    """Test fetching an image with a specific width and height."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    get_image_mock = AsyncMock()
    with patch(
        "menuai.components.ffmpeg.ImageFrame",
        return_value=Mock(get_image=get_image_mock),
    ):
        await ffmpeg.async_get_image(menuai, "rtsp://fake", width=640, height=480)

    assert get_image_mock.call_args_list == [
        call("rtsp://fake", output_format="mjpeg", extra_cmd="-s 640x480")
    ]


async def test_async_get_image_with_extra_cmd_overlapping_width_height(
    menuai: menuai,
) -> None:
    """Test fetching an image with and extra_cmd with width and height and a specific width and height."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    get_image_mock = AsyncMock()
    with patch(
        "menuai.components.ffmpeg.ImageFrame",
        return_value=Mock(get_image=get_image_mock),
    ):
        await ffmpeg.async_get_image(
            menuai, "rtsp://fake", extra_cmd="-s 1024x768", width=640, height=480
        )

    assert get_image_mock.call_args_list == [
        call("rtsp://fake", output_format="mjpeg", extra_cmd="-s 1024x768")
    ]


async def test_async_get_image_with_extra_cmd_width_height(menuai: menuai) -> None:
    """Test fetching an image with and extra_cmd and a specific width and height."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    get_image_mock = AsyncMock()
    with patch(
        "menuai.components.ffmpeg.ImageFrame",
        return_value=Mock(get_image=get_image_mock),
    ):
        await ffmpeg.async_get_image(
            menuai, "rtsp://fake", extra_cmd="-vf any", width=640, height=480
        )

    assert get_image_mock.call_args_list == [
        call("rtsp://fake", output_format="mjpeg", extra_cmd="-vf any -s 640x480")
    ]


async def test_modern_ffmpeg(
    menuai: menuai,
) -> None:
    """Test modern ffmpeg uses the new ffmpeg content type."""
    with assert_setup_component(1):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    manager = get_ffmpeg_manager(menuai)
    assert "ffmpeg" in manager.ffmpeg_stream_content_type


async def test_legacy_ffmpeg(
    menuai: menuai,
) -> None:
    """Test legacy ffmpeg uses the old ffserver content type."""
    with (
        assert_setup_component(1),
        patch(
            "menuai.components.ffmpeg.FFVersion.get_version", return_value="3.0"
        ),
        patch("menuai.components.ffmpeg.is_official_image", return_value=False),
    ):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    manager = get_ffmpeg_manager(menuai)
    assert "ffserver" in manager.ffmpeg_stream_content_type


async def test_ffmpeg_using_official_image(
    menuai: menuai,
) -> None:
    """Test ffmpeg using official image is the new ffmpeg content type."""
    with (
        assert_setup_component(1),
        patch("menuai.components.ffmpeg.is_official_image", return_value=True),
    ):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    manager = get_ffmpeg_manager(menuai)
    assert "ffmpeg" in manager.ffmpeg_stream_content_type
