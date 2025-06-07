"""Test helpers for camera."""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest
from webrtc_models import RTCIceCandidateInit

from menuai.components import camera
from menuai.components.camera.const import StreamType
from menuai.components.camera.webrtc import WebRTCAnswer, WebRTCSendMessage
from menuai.config_entries import ConfigEntry, ConfigFlow
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.device_registry import DeviceInfo
from menuai.setup import async_setup_component

from .common import STREAM_SOURCE, WEBRTC_ANSWER, SomeTestProvider

from tests.common import (
    MockConfigEntry,
    MockModule,
    mock_config_flow,
    mock_integration,
    mock_platform,
    setup_test_component_platform,
)


@pytest.fixture(autouse=True)
async def setup_menuai(menuai: menuai) -> None:
    """Set up the menuai integration."""
    await async_setup_component(menuai, "menuai", {})


@pytest.fixture(autouse=True)
def camera_only() -> Generator[None]:
    """Enable only the camera platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.CAMERA],
    ):
        yield


@pytest.fixture(name="mock_camera")
async def mock_camera_fixture(menuai: menuai) -> AsyncGenerator[None]:
    """Initialize a demo camera platform."""
    assert await async_setup_component(
        menuai, "camera", {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    with patch(
        "menuai.components.demo.camera.Path.read_bytes",
        return_value=b"Test",
    ):
        yield


@pytest.fixture(name="mock_camera_hls")
def mock_camera_hls_fixture(mock_camera: None) -> Generator[None]:
    """Initialize a demo camera platform with HLS."""
    with patch(
        "menuai.components.camera.Camera.camera_capabilities",
        new_callable=PropertyMock(
            return_value=camera.CameraCapabilities({StreamType.HLS})
        ),
    ):
        yield


@pytest.fixture
async def mock_camera_webrtc(
    mock_camera: None,
) -> AsyncGenerator[None]:
    """Initialize a demo camera platform with WebRTC."""

    async def async_handle_async_webrtc_offer(
        offer_sdp: str, session_id: str, send_message: WebRTCSendMessage
    ) -> None:
        send_message(WebRTCAnswer(WEBRTC_ANSWER))

    with (
        patch(
            "menuai.components.camera.Camera.async_handle_async_webrtc_offer",
            side_effect=async_handle_async_webrtc_offer,
        ),
        patch(
            "menuai.components.camera.Camera.camera_capabilities",
            new_callable=PropertyMock(
                return_value=camera.CameraCapabilities({StreamType.WEB_RTC})
            ),
        ),
    ):
        yield


@pytest.fixture(name="mock_camera_with_device")
def mock_camera_with_device_fixture() -> Generator[None]:
    """Initialize a demo camera platform with a device."""
    dev_info = DeviceInfo(
        identifiers={("camera", "test_unique_id")},
        name="Test Camera Device",
    )

    class UniqueIdMock(PropertyMock):
        def __get__(self, obj, obj_type=None):
            return obj.name

    with (
        patch(
            "menuai.components.camera.Camera.has_entity_name",
            new_callable=PropertyMock(return_value=True),
        ),
        patch("menuai.components.camera.Camera.unique_id", new=UniqueIdMock()),
        patch(
            "menuai.components.camera.Camera.device_info",
            new_callable=PropertyMock(return_value=dev_info),
        ),
    ):
        yield


@pytest.fixture(name="mock_camera_with_no_name")
def mock_camera_with_no_name_fixture(mock_camera_with_device: None) -> Generator[None]:
    """Initialize a demo camera platform with a device and no name."""
    with patch(
        "menuai.components.camera.Camera._attr_name",
        new_callable=PropertyMock(return_value=None),
    ):
        yield


@pytest.fixture(name="mock_stream")
async def mock_stream_fixture(menuai: menuai) -> None:
    """Initialize a demo camera platform with streaming."""
    assert await async_setup_component(menuai, "stream", {"stream": {}})


@pytest.fixture(name="mock_stream_source")
def mock_stream_source_fixture() -> Generator[AsyncMock]:
    """Fixture to create an RTSP stream source."""
    with patch(
        "menuai.components.camera.Camera.stream_source",
        return_value=STREAM_SOURCE,
    ) as mock_stream_source:
        yield mock_stream_source


@pytest.fixture
async def mock_test_webrtc_cameras(menuai: menuai) -> None:
    """Initialize test WebRTC cameras with native RTC support."""

    # Cannot use the fixture mock_camera_web_rtc as it's mocking Camera.async_handle_web_rtc_offer
    # and native support is checked by verify the function "async_handle_web_rtc_offer" was
    # overwritten(implemented) or not
    class BaseCamera(camera.Camera):
        """Base Camera."""

        _attr_supported_features: camera.CameraEntityFeature = (
            camera.CameraEntityFeature.STREAM
        )

        async def stream_source(self) -> str | None:
            return STREAM_SOURCE

    class AsyncNoCandidateCamera(BaseCamera):
        """Mock Camera with native async WebRTC support but not implemented candidate support."""

        _attr_name = "Async No Candidate"

        async def async_handle_async_webrtc_offer(
            self, offer_sdp: str, session_id: str, send_message: WebRTCSendMessage
        ) -> None:
            send_message(WebRTCAnswer(WEBRTC_ANSWER))

    class AsyncCamera(BaseCamera):
        """Mock Camera with native async WebRTC support."""

        _attr_name = "Async"

        async def async_handle_async_webrtc_offer(
            self, offer_sdp: str, session_id: str, send_message: WebRTCSendMessage
        ) -> None:
            send_message(WebRTCAnswer(WEBRTC_ANSWER))

        async def async_on_webrtc_candidate(
            self, session_id: str, candidate: RTCIceCandidateInit
        ) -> None:
            """Handle a WebRTC candidate."""
            # Do nothing

    domain = "test"

    entry = MockConfigEntry(domain=domain)
    entry.add_to_menuai(menuai)

    async def async_setup_entry_init(
        menuai: menuai, config_entry: ConfigEntry
    ) -> bool:
        """Set up test config entry."""
        await menuai.config_entries.async_forward_entry_setups(
            config_entry, [Platform.CAMERA]
        )
        return True

    async def async_unload_entry_init(
        menuai: menuai, config_entry: ConfigEntry
    ) -> bool:
        """Unload test config entry."""
        await menuai.config_entries.async_forward_entry_unload(
            config_entry, Platform.CAMERA
        )
        return True

    mock_integration(
        menuai,
        MockModule(
            domain,
            async_setup_entry=async_setup_entry_init,
            async_unload_entry=async_unload_entry_init,
        ),
    )
    setup_test_component_platform(
        menuai,
        camera.DOMAIN,
        [AsyncNoCandidateCamera(), AsyncCamera()],
        from_config_entry=True,
    )
    mock_platform(menuai, f"{domain}.config_flow", Mock())

    with mock_config_flow(domain, ConfigFlow):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()


@pytest.fixture
async def register_test_provider(
    menuai: menuai,
) -> AsyncGenerator[SomeTestProvider]:
    """Add WebRTC test provider."""
    await async_setup_component(menuai, "camera", {})

    provider = SomeTestProvider()
    unsub = camera.async_register_webrtc_provider(menuai, provider)
    await menuai.async_block_till_done()
    yield provider
    unsub()
