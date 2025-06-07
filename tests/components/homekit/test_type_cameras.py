"""Test different accessory types: Camera."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from uuid import UUID

import pytest

from menuai.components import camera, ffmpeg
from menuai.components.binary_sensor import BinarySensorDeviceClass
from menuai.components.camera.img_util import TurboJPEGSingleton
from menuai.components.event import EventDeviceClass
from menuai.components.homekit.accessories import HomeBridge
from menuai.components.homekit.const import (
    AUDIO_CODEC_COPY,
    CHAR_MOTION_DETECTED,
    CHAR_PROGRAMMABLE_SWITCH_EVENT,
    CONF_AUDIO_CODEC,
    CONF_LINKED_DOORBELL_SENSOR,
    CONF_LINKED_MOTION_SENSOR,
    CONF_STREAM_SOURCE,
    CONF_SUPPORT_AUDIO,
    CONF_VIDEO_CODEC,
    CONF_VIDEO_PROFILE_NAMES,
    SERV_DOORBELL,
    SERV_MOTION_SENSOR,
    SERV_STATELESS_PROGRAMMABLE_SWITCH,
    VIDEO_CODEC_COPY,
    VIDEO_CODEC_H264_OMX,
    VIDEO_CODEC_H264_V4L2M2M,
)
from menuai.components.homekit.type_cameras import Camera
from menuai.components.homekit.type_switches import Switch
from menuai.const import (
    ATTR_DEVICE_CLASS,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.components.camera.common import mock_turbo_jpeg

MOCK_START_STREAM_TLV = "ARUCAQEBEDMD1QMXzEaatnKSQ2pxovYCNAEBAAIJAQECAgECAwEAAwsBAgAFAgLQAgMBHgQXAQFjAgQ768/RAwIrAQQEAAAAPwUCYgUDLAEBAwIMAQEBAgEAAwECBAEUAxYBAW4CBCzq28sDAhgABAQAAKBABgENBAEA"
MOCK_END_POINTS_TLV = "ARAzA9UDF8xGmrZykkNqcaL2AgEAAxoBAQACDTE5Mi4xNjguMjA4LjUDAi7IBAKkxwQlAQEAAhDN0+Y0tZ4jzoO0ske9UsjpAw6D76oVXnoi7DbawIG4CwUlAQEAAhCyGcROB8P7vFRDzNF2xrK1Aw6NdcLugju9yCfkWVSaVAYEDoAsAAcEpxV8AA=="
MOCK_START_STREAM_SESSION_UUID = UUID("3303d503-17cc-469a-b672-92436a71a2f6")

PID_THAT_WILL_NEVER_BE_ALIVE = 2147483647


@pytest.fixture(autouse=True)
async def setup_menuai(menuai: menuai) -> None:
    """Set up the menuai integration."""
    await async_setup_component(menuai, "menuai", {})


async def _async_start_streaming(menuai: menuai, acc: Camera) -> None:
    """Start streaming a camera."""
    acc.set_selected_stream_configuration(MOCK_START_STREAM_TLV)
    await menuai.async_block_till_done()
    acc.run()
    await menuai.async_block_till_done()


async def _async_setup_endpoints(menuai: menuai, acc: Camera) -> None:
    """Set camera endpoints."""
    acc.set_endpoints(MOCK_END_POINTS_TLV)
    acc.run()
    await menuai.async_block_till_done()


async def _async_reconfigure_stream(
    menuai: menuai,
    acc: Camera,
    session_info: dict[str, Any],
    stream_config: dict[str, Any],
) -> None:
    """Reconfigure the stream."""
    await acc.reconfigure_stream(session_info, stream_config)
    acc.run()
    await menuai.async_block_till_done()


async def _async_stop_all_streams(menuai: menuai, acc: Camera) -> None:
    """Stop all camera streams."""
    await acc.stop()
    acc.run()
    await menuai.async_block_till_done()


async def _async_stop_stream(
    menuai: menuai, acc: Camera, session_info: dict[str, Any]
) -> None:
    """Stop a camera stream."""
    await acc.stop_stream(session_info)
    acc.run()
    await menuai.async_block_till_done()


def _mock_reader():
    """Mock ffmpeg reader."""

    async def _readline(*args, **kwargs):
        await asyncio.sleep(0.1)

    async def _get_reader(*args, **kwargs):
        return AsyncMock(readline=_readline)

    return _get_reader


def _get_exits_after_startup_mock_ffmpeg():
    """Return a ffmpeg that will have an invalid pid."""
    ffmpeg = MagicMock()
    type(ffmpeg.process).pid = PropertyMock(return_value=PID_THAT_WILL_NEVER_BE_ALIVE)
    ffmpeg.open = AsyncMock(return_value=True)
    ffmpeg.close = AsyncMock(return_value=True)
    ffmpeg.kill = AsyncMock(return_value=True)
    ffmpeg.get_reader = _mock_reader()
    return ffmpeg


def _get_working_mock_ffmpeg():
    """Return a working ffmpeg."""
    ffmpeg = MagicMock()
    ffmpeg.open = AsyncMock(return_value=True)
    ffmpeg.close = AsyncMock(return_value=True)
    ffmpeg.kill = AsyncMock(return_value=True)
    ffmpeg.get_reader = _mock_reader()
    return ffmpeg


def _get_failing_mock_ffmpeg():
    """Return an ffmpeg that fails to shutdown."""
    ffmpeg = MagicMock()
    type(ffmpeg.process).pid = PropertyMock(return_value=PID_THAT_WILL_NEVER_BE_ALIVE)
    ffmpeg.open = AsyncMock(return_value=False)
    ffmpeg.close = AsyncMock(side_effect=OSError)
    ffmpeg.kill = AsyncMock(side_effect=OSError)
    ffmpeg.get_reader = _mock_reader()
    return ffmpeg


async def test_camera_stream_source_configured(menuai: menuai, run_driver) -> None:
    """Test a camera that can stream with a configured source."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {CONF_STREAM_SOURCE: "/dev/null", CONF_SUPPORT_AUDIO: True},
    )
    not_camera_acc = Switch(
        menuai,
        run_driver,
        "Switch",
        entity_id,
        4,
        {},
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)
    bridge.add_accessory(not_camera_acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    await _async_setup_endpoints(menuai, acc)
    working_ffmpeg = _get_working_mock_ffmpeg()
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    with (
        patch(
            "menuai.components.demo.camera.DemoCamera.stream_source",
            return_value=None,
        ),
        patch(
            "menuai.components.homekit.type_cameras.HAFFmpeg",
            return_value=working_ffmpeg,
        ),
    ):
        await _async_start_streaming(menuai, acc)
        await _async_stop_all_streams(menuai, acc)

    expected_output = (
        "-map 0:v:0 -an -c:v libx264 -profile:v high -tune zerolatency -pix_fmt "
        "yuv420p -r 30 -b:v 299k -bufsize 1196k -maxrate 299k -payload_type 99 -ssrc {v_ssrc} -f "
        "rtp -srtp_out_suite AES_CM_128_HMAC_SHA1_80 -srtp_out_params "
        "zdPmNLWeI86DtLJHvVLI6YPvqhVeeiLsNtrAgbgL "
        "srtp://192.168.208.5:51246?rtcpport=51246&localrtpport=51246&pkt_size=1316 -map 0:a:0 "
        "-vn -c:a libopus -application lowdelay -ac 1 -ar 24k -b:a 24k -bufsize 96k -payload_type "
        "110 -ssrc {a_ssrc} -f rtp -srtp_out_suite AES_CM_128_HMAC_SHA1_80 -srtp_out_params "
        "shnETgfD+7xUQ8zRdsaytY11wu6CO73IJ+RZVJpU "
        "srtp://192.168.208.5:51108?rtcpport=51108&localrtpport=51108&pkt_size=188"
    )

    working_ffmpeg.open.assert_called_with(
        cmd=[],
        input_source="-i /dev/null",
        output=expected_output.format(**session_info),
        stdout_pipe=False,
        extra_cmd="-hide_banner -nostats",
        stderr_pipe=True,
    )

    await _async_setup_endpoints(menuai, acc)
    working_ffmpeg = _get_working_mock_ffmpeg()
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    with (
        patch(
            "menuai.components.demo.camera.DemoCamera.stream_source",
            return_value="rtsp://example.local",
        ),
        patch(
            "menuai.components.homekit.type_cameras.HAFFmpeg",
            return_value=working_ffmpeg,
        ),
    ):
        await _async_start_streaming(menuai, acc)
        await _async_stop_all_streams(menuai, acc)
        # Calling a second time should not throw
        await _async_stop_all_streams(menuai, acc)

    turbo_jpeg = mock_turbo_jpeg(
        first_width=16, first_height=12, second_width=300, second_height=200
    )
    with patch("turbojpeg.TurboJPEG", return_value=turbo_jpeg):
        TurboJPEGSingleton()
        assert await acc.async_get_snapshot(
            {"aid": 2, "image-width": 300, "image-height": 200}
        )
        # Verify the bridge only forwards async_get_snapshot for
        # cameras and valid accessory ids
        assert await bridge.async_get_snapshot(
            {"aid": 2, "image-width": 300, "image-height": 200}
        )

    with pytest.raises(ValueError):
        assert await bridge.async_get_snapshot(
            {"aid": 3, "image-width": 300, "image-height": 200}
        )

    with pytest.raises(ValueError):
        assert await bridge.async_get_snapshot(
            {"aid": 4, "image-width": 300, "image-height": 200}
        )


async def test_camera_stream_source_configured_with_failing_ffmpeg(
    menuai: menuai, run_driver
) -> None:
    """Test a camera that can stream with a configured source with ffmpeg failing."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {CONF_STREAM_SOURCE: "/dev/null", CONF_SUPPORT_AUDIO: True},
    )
    not_camera_acc = Switch(
        menuai,
        run_driver,
        "Switch",
        entity_id,
        4,
        {},
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)
    bridge.add_accessory(not_camera_acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    await _async_setup_endpoints(menuai, acc)

    with (
        patch(
            "menuai.components.demo.camera.DemoCamera.stream_source",
            return_value="rtsp://example.local",
        ),
        patch(
            "menuai.components.homekit.type_cameras.HAFFmpeg",
            return_value=_get_failing_mock_ffmpeg(),
        ),
    ):
        await _async_start_streaming(menuai, acc)
        await _async_stop_all_streams(menuai, acc)
        # Calling a second time should not throw
        await _async_stop_all_streams(menuai, acc)


async def test_camera_stream_source_found(menuai: menuai, run_driver) -> None:
    """Test a camera that can stream and we get the source from the entity."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {},
    )
    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    await _async_setup_endpoints(menuai, acc)
    working_ffmpeg = _get_working_mock_ffmpeg()
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    with (
        patch(
            "menuai.components.demo.camera.DemoCamera.stream_source",
            return_value="rtsp://example.local",
        ),
        patch(
            "menuai.components.homekit.type_cameras.HAFFmpeg",
            return_value=working_ffmpeg,
        ),
    ):
        await _async_start_streaming(menuai, acc)
        await _async_stop_all_streams(menuai, acc)

    expected_output = (
        "-map 0:v:0 -an -c:v libx264 -profile:v high -tune zerolatency -pix_fmt "
        "yuv420p -r 30 -b:v 299k -bufsize 1196k -maxrate 299k -payload_type 99 -ssrc {v_ssrc} -f "
        "rtp -srtp_out_suite AES_CM_128_HMAC_SHA1_80 -srtp_out_params "
        "zdPmNLWeI86DtLJHvVLI6YPvqhVeeiLsNtrAgbgL "
        "srtp://192.168.208.5:51246?rtcpport=51246&localrtpport=51246&pkt_size=1316"
    )

    working_ffmpeg.open.assert_called_with(
        cmd=[],
        input_source="-i rtsp://example.local",
        output=expected_output.format(**session_info),
        stdout_pipe=False,
        extra_cmd="-hide_banner -nostats",
        stderr_pipe=True,
    )

    await _async_setup_endpoints(menuai, acc)
    working_ffmpeg = _get_working_mock_ffmpeg()
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    with (
        patch(
            "menuai.components.demo.camera.DemoCamera.stream_source",
            return_value="rtsp://example2.local",
        ),
        patch(
            "menuai.components.homekit.type_cameras.HAFFmpeg",
            return_value=working_ffmpeg,
        ),
    ):
        await _async_start_streaming(menuai, acc)
        await _async_stop_all_streams(menuai, acc)

    working_ffmpeg.open.assert_called_with(
        cmd=[],
        input_source="-i rtsp://example2.local",
        output=expected_output.format(**session_info),
        stdout_pipe=False,
        extra_cmd="-hide_banner -nostats",
        stderr_pipe=True,
    )


async def test_camera_stream_source_fails(menuai: menuai, run_driver) -> None:
    """Test a camera that can stream and we cannot get the source from the entity."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {},
    )
    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    await _async_setup_endpoints(menuai, acc)

    with (
        patch(
            "menuai.components.demo.camera.DemoCamera.stream_source",
            side_effect=OSError,
        ),
        patch(
            "menuai.components.homekit.type_cameras.HAFFmpeg",
            return_value=_get_working_mock_ffmpeg(),
        ),
    ):
        await _async_start_streaming(menuai, acc)
        await _async_stop_all_streams(menuai, acc)


async def test_camera_with_no_stream(menuai: menuai, run_driver) -> None:
    """Test a camera that cannot stream."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(menuai, camera.DOMAIN, {camera.DOMAIN: {}})

    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {},
    )
    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    await _async_setup_endpoints(menuai, acc)
    await _async_start_streaming(menuai, acc)
    await _async_stop_all_streams(menuai, acc)

    with pytest.raises(menuaiError):
        assert await acc.async_get_snapshot(
            {"aid": 2, "image-width": 300, "image-height": 200}
        )


async def test_camera_stream_source_configured_and_copy_codec(
    menuai: menuai, run_driver
) -> None:
    """Test a camera that can stream with a configured source."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {
            CONF_STREAM_SOURCE: "/dev/null",
            CONF_SUPPORT_AUDIO: True,
            CONF_VIDEO_CODEC: VIDEO_CODEC_COPY,
            CONF_AUDIO_CODEC: AUDIO_CODEC_COPY,
        },
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    await _async_setup_endpoints(menuai, acc)
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    working_ffmpeg = _get_working_mock_ffmpeg()

    with (
        patch(
            "menuai.components.demo.camera.DemoCamera.stream_source",
            return_value=None,
        ),
        patch(
            "menuai.components.homekit.type_cameras.HAFFmpeg",
            return_value=working_ffmpeg,
        ),
    ):
        await _async_start_streaming(menuai, acc)
        await _async_reconfigure_stream(menuai, acc, session_info, {})
        await _async_stop_all_streams(menuai, acc)

    expected_output = (
        "-map 0:v:0 -an -c:v copy -tune zerolatency -pix_fmt yuv420p -r 30 -b:v 299k "
        "-bufsize 1196k -maxrate 299k -payload_type 99 -ssrc {v_ssrc} -f rtp -srtp_out_suite "
        "AES_CM_128_HMAC_SHA1_80 -srtp_out_params zdPmNLWeI86DtLJHvVLI6YPvqhVeeiLsNtrAgbgL "
        "srtp://192.168.208.5:51246?rtcpport=51246&localrtpport=51246&pkt_size=1316 -map 0:a:0 "
        "-vn -c:a copy -ac 1 -ar 24k -b:a 24k -bufsize 96k -payload_type 110 -ssrc {a_ssrc} "
        "-f rtp -srtp_out_suite AES_CM_128_HMAC_SHA1_80 -srtp_out_params "
        "shnETgfD+7xUQ8zRdsaytY11wu6CO73IJ+RZVJpU "
        "srtp://192.168.208.5:51108?rtcpport=51108&localrtpport=51108&pkt_size=188"
    )

    working_ffmpeg.open.assert_called_with(
        cmd=[],
        input_source="-i /dev/null",
        output=expected_output.format(**session_info),
        stdout_pipe=False,
        extra_cmd="-hide_banner -nostats",
        stderr_pipe=True,
    )


async def test_camera_stream_source_configured_and_override_profile_names(
    menuai: menuai, run_driver
) -> None:
    """Test a camera that can stream with a configured source over overridden profile names."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {
            CONF_STREAM_SOURCE: "/dev/null",
            CONF_SUPPORT_AUDIO: True,
            CONF_VIDEO_CODEC: VIDEO_CODEC_H264_V4L2M2M,
            CONF_VIDEO_PROFILE_NAMES: ["0", "2", "4"],
            CONF_AUDIO_CODEC: AUDIO_CODEC_COPY,
        },
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    await _async_setup_endpoints(menuai, acc)
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    working_ffmpeg = _get_working_mock_ffmpeg()

    with (
        patch(
            "menuai.components.demo.camera.DemoCamera.stream_source",
            return_value=None,
        ),
        patch(
            "menuai.components.homekit.type_cameras.HAFFmpeg",
            return_value=working_ffmpeg,
        ),
    ):
        await _async_start_streaming(menuai, acc)
        await _async_reconfigure_stream(menuai, acc, session_info, {})
        await _async_stop_all_streams(menuai, acc)

    expected_output = (
        "-map 0:v:0 -an -c:v h264_v4l2m2m -profile:v 4 -tune zerolatency -pix_fmt yuv420p -r 30 -b:v 299k "
        "-bufsize 1196k -maxrate 299k -payload_type 99 -ssrc {v_ssrc} -f rtp -srtp_out_suite "
        "AES_CM_128_HMAC_SHA1_80 -srtp_out_params zdPmNLWeI86DtLJHvVLI6YPvqhVeeiLsNtrAgbgL "
        "srtp://192.168.208.5:51246?rtcpport=51246&localrtpport=51246&pkt_size=1316 -map 0:a:0 "
        "-vn -c:a copy -ac 1 -ar 24k -b:a 24k -bufsize 96k -payload_type 110 -ssrc {a_ssrc} "
        "-f rtp -srtp_out_suite AES_CM_128_HMAC_SHA1_80 -srtp_out_params "
        "shnETgfD+7xUQ8zRdsaytY11wu6CO73IJ+RZVJpU "
        "srtp://192.168.208.5:51108?rtcpport=51108&localrtpport=51108&pkt_size=188"
    )

    working_ffmpeg.open.assert_called_with(
        cmd=[],
        input_source="-i /dev/null",
        output=expected_output.format(**session_info),
        stdout_pipe=False,
        extra_cmd="-hide_banner -nostats",
        stderr_pipe=True,
    )


async def test_camera_streaming_fails_after_starting_ffmpeg(
    menuai: menuai, run_driver
) -> None:
    """Test a camera that can stream with a configured source."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()

    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {
            CONF_STREAM_SOURCE: "/dev/null",
            CONF_SUPPORT_AUDIO: True,
            CONF_VIDEO_CODEC: VIDEO_CODEC_H264_OMX,
            CONF_AUDIO_CODEC: AUDIO_CODEC_COPY,
        },
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    await _async_setup_endpoints(menuai, acc)
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    ffmpeg_with_invalid_pid = _get_exits_after_startup_mock_ffmpeg()

    with (
        patch(
            "menuai.components.demo.camera.DemoCamera.stream_source",
            return_value=None,
        ),
        patch(
            "menuai.components.homekit.type_cameras.HAFFmpeg",
            return_value=ffmpeg_with_invalid_pid,
        ),
    ):
        await _async_start_streaming(menuai, acc)
        await _async_reconfigure_stream(menuai, acc, session_info, {})
        # Should not throw
        await _async_stop_stream(menuai, acc, {"id": "does_not_exist"})
        await _async_stop_all_streams(menuai, acc)

    expected_output = (
        "-map 0:v:0 -an -c:v h264_omx -profile:v high -tune zerolatency -pix_fmt yuv420p -r 30 -b:v 299k "
        "-bufsize 1196k -maxrate 299k -payload_type 99 -ssrc {v_ssrc} -f rtp -srtp_out_suite "
        "AES_CM_128_HMAC_SHA1_80 -srtp_out_params zdPmNLWeI86DtLJHvVLI6YPvqhVeeiLsNtrAgbgL "
        "srtp://192.168.208.5:51246?rtcpport=51246&localrtpport=51246&pkt_size=1316 -map 0:a:0 "
        "-vn -c:a copy -ac 1 -ar 24k -b:a 24k -bufsize 96k -payload_type 110 -ssrc {a_ssrc} "
        "-f rtp -srtp_out_suite AES_CM_128_HMAC_SHA1_80 -srtp_out_params "
        "shnETgfD+7xUQ8zRdsaytY11wu6CO73IJ+RZVJpU "
        "srtp://192.168.208.5:51108?rtcpport=51108&localrtpport=51108&pkt_size=188"
    )

    ffmpeg_with_invalid_pid.open.assert_called_with(
        cmd=[],
        input_source="-i /dev/null",
        output=expected_output.format(**session_info),
        stdout_pipe=False,
        extra_cmd="-hide_banner -nostats",
        stderr_pipe=True,
    )


async def test_camera_with_linked_motion_sensor(
    menuai: menuai, run_driver
) -> None:
    """Test a camera with a linked motion sensor can update."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    motion_entity_id = "binary_sensor.motion"

    menuai.states.async_set(
        motion_entity_id, STATE_ON, {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.MOTION}
    )
    await menuai.async_block_till_done()
    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {
            CONF_STREAM_SOURCE: "/dev/null",
            CONF_SUPPORT_AUDIO: True,
            CONF_VIDEO_CODEC: VIDEO_CODEC_H264_OMX,
            CONF_AUDIO_CODEC: AUDIO_CODEC_COPY,
            CONF_LINKED_MOTION_SENSOR: motion_entity_id,
        },
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    service = acc.get_service(SERV_MOTION_SENSOR)
    assert service
    char = service.get_characteristic(CHAR_MOTION_DETECTED)
    assert char

    assert char.value is True
    broker = MagicMock()
    char.broker = broker

    menuai.states.async_set(
        motion_entity_id, STATE_OFF, {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.MOTION}
    )
    await menuai.async_block_till_done()
    assert len(broker.mock_calls) == 2
    broker.reset_mock()
    assert char.value is False

    char.set_value(True)
    menuai.states.async_set(
        motion_entity_id, STATE_ON, {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.MOTION}
    )
    await menuai.async_block_till_done()
    assert len(broker.mock_calls) == 2
    broker.reset_mock()
    assert char.value is True

    menuai.states.async_set(
        motion_entity_id,
        STATE_ON,
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.MOTION},
        force_update=True,
    )
    await menuai.async_block_till_done()
    assert len(broker.mock_calls) == 0
    broker.reset_mock()

    menuai.states.async_set(
        motion_entity_id,
        STATE_ON,
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.MOTION, "other": "attr"},
    )
    await menuai.async_block_till_done()
    assert len(broker.mock_calls) == 0
    broker.reset_mock()
    # Ensure we do not throw when the linked
    # motion sensor is removed
    menuai.states.async_remove(motion_entity_id)
    await menuai.async_block_till_done()
    acc.run()
    await menuai.async_block_till_done()
    assert char.value is True


async def test_camera_with_linked_motion_event(menuai: menuai, run_driver) -> None:
    """Test a camera with a linked motion event entity can update."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    motion_entity_id = "event.motion"

    menuai.states.async_set(
        motion_entity_id,
        dt_util.utcnow().isoformat(),
        {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION},
    )
    await menuai.async_block_till_done()
    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {
            CONF_STREAM_SOURCE: "/dev/null",
            CONF_SUPPORT_AUDIO: True,
            CONF_VIDEO_CODEC: VIDEO_CODEC_H264_OMX,
            CONF_AUDIO_CODEC: AUDIO_CODEC_COPY,
            CONF_LINKED_MOTION_SENSOR: motion_entity_id,
        },
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    service = acc.get_service(SERV_MOTION_SENSOR)
    assert service
    char = service.get_characteristic(CHAR_MOTION_DETECTED)
    assert char

    assert char.value is False
    broker = MagicMock()
    char.broker = broker

    menuai.states.async_set(
        motion_entity_id, STATE_UNKNOWN, {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION}
    )
    await menuai.async_block_till_done()
    assert len(broker.mock_calls) == 0
    broker.reset_mock()
    assert char.value is False

    char.set_value(True)
    fire_time = dt_util.utcnow().isoformat()
    menuai.states.async_set(
        motion_entity_id, fire_time, {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION}
    )
    await menuai.async_block_till_done()
    assert len(broker.mock_calls) == 4
    broker.reset_mock()
    assert char.value is False

    menuai.states.async_set(
        motion_entity_id,
        fire_time,
        {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION},
        force_update=True,
    )
    await menuai.async_block_till_done()
    assert len(broker.mock_calls) == 0
    broker.reset_mock()

    menuai.states.async_set(
        motion_entity_id,
        fire_time,
        {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION, "other": "attr"},
    )
    await menuai.async_block_till_done()
    assert len(broker.mock_calls) == 0
    broker.reset_mock()
    # Ensure we do not throw when the linked
    # motion sensor is removed
    menuai.states.async_remove(motion_entity_id)
    await menuai.async_block_till_done()
    acc.run()
    await menuai.async_block_till_done()
    assert char.value is False

    # Ensure re-adding does not fire an event
    menuai.states.async_set(
        motion_entity_id,
        dt_util.utcnow().isoformat(),
        {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION, "other": "attr"},
    )
    await menuai.async_block_till_done()
    assert not broker.mock_calls

    # But a second update does
    broker.reset_mock()
    menuai.states.async_set(
        motion_entity_id,
        dt_util.utcnow().isoformat(),
        {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION},
    )
    await menuai.async_block_till_done()
    assert broker.mock_calls

    # Now go unavailable
    broker.reset_mock()
    menuai.states.async_set(
        motion_entity_id,
        STATE_UNAVAILABLE,
        {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION},
    )
    await menuai.async_block_till_done()
    assert not broker.mock_calls

    # Going from unavailable to a state should not fire an event
    menuai.states.async_set(
        motion_entity_id,
        dt_util.utcnow().isoformat(),
        {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION},
    )
    await menuai.async_block_till_done()
    assert not broker.mock_calls

    # But a another update does
    broker.reset_mock()
    menuai.states.async_set(
        motion_entity_id,
        dt_util.utcnow().isoformat(),
        {ATTR_DEVICE_CLASS: EventDeviceClass.MOTION, "other": "attr"},
    )
    await menuai.async_block_till_done()
    assert broker.mock_calls


async def test_camera_with_a_missing_linked_motion_sensor(
    menuai: menuai, run_driver
) -> None:
    """Test a camera with a configured linked motion sensor that is missing."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    motion_entity_id = "binary_sensor.motion"
    entity_id = "camera.demo_camera"
    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {CONF_LINKED_MOTION_SENSOR: motion_entity_id},
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    assert not acc.get_service(SERV_MOTION_SENSOR)


async def test_camera_with_linked_doorbell_sensor(
    menuai: menuai, run_driver
) -> None:
    """Test a camera with a linked doorbell sensor can update."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    doorbell_entity_id = "binary_sensor.doorbell"

    menuai.states.async_set(
        doorbell_entity_id,
        STATE_ON,
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.OCCUPANCY},
    )
    await menuai.async_block_till_done()
    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {
            CONF_STREAM_SOURCE: "/dev/null",
            CONF_SUPPORT_AUDIO: True,
            CONF_VIDEO_CODEC: VIDEO_CODEC_H264_OMX,
            CONF_AUDIO_CODEC: AUDIO_CODEC_COPY,
            CONF_LINKED_DOORBELL_SENSOR: doorbell_entity_id,
        },
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    service = acc.get_service(SERV_DOORBELL)
    assert service
    char = service.get_characteristic(CHAR_PROGRAMMABLE_SWITCH_EVENT)
    assert char

    assert char.value is None

    service2 = acc.get_service(SERV_STATELESS_PROGRAMMABLE_SWITCH)
    assert service2
    char2 = service.get_characteristic(CHAR_PROGRAMMABLE_SWITCH_EVENT)
    assert char2
    broker = MagicMock()
    char2.broker = broker
    assert char2.value is None

    menuai.states.async_set(
        doorbell_entity_id,
        STATE_OFF,
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.OCCUPANCY},
    )
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None
    assert len(broker.mock_calls) == 0

    char.set_value(True)
    char2.set_value(True)
    broker.reset_mock()

    menuai.states.async_set(
        doorbell_entity_id,
        STATE_ON,
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.OCCUPANCY},
    )
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None
    assert len(broker.mock_calls) == 2
    broker.reset_mock()

    menuai.states.async_set(
        doorbell_entity_id,
        STATE_ON,
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.OCCUPANCY},
        force_update=True,
    )
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None
    assert len(broker.mock_calls) == 0
    broker.reset_mock()

    menuai.states.async_set(
        doorbell_entity_id,
        STATE_ON,
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.OCCUPANCY, "other": "attr"},
    )
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None
    assert len(broker.mock_calls) == 0
    broker.reset_mock()

    # Ensure we do not throw when the linked
    # doorbell sensor is removed
    menuai.states.async_remove(doorbell_entity_id)
    await menuai.async_block_till_done()
    acc.run()
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None


async def test_camera_with_linked_doorbell_event(
    menuai: menuai, run_driver
) -> None:
    """Test a camera with a linked doorbell event can update."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    doorbell_entity_id = "event.doorbell"

    menuai.states.async_set(
        doorbell_entity_id,
        dt_util.utcnow().isoformat(),
        {ATTR_DEVICE_CLASS: EventDeviceClass.DOORBELL},
    )
    await menuai.async_block_till_done()
    entity_id = "camera.demo_camera"

    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {
            CONF_STREAM_SOURCE: "/dev/null",
            CONF_SUPPORT_AUDIO: True,
            CONF_VIDEO_CODEC: VIDEO_CODEC_H264_OMX,
            CONF_AUDIO_CODEC: AUDIO_CODEC_COPY,
            CONF_LINKED_DOORBELL_SENSOR: doorbell_entity_id,
        },
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    service = acc.get_service(SERV_DOORBELL)
    assert service
    char = service.get_characteristic(CHAR_PROGRAMMABLE_SWITCH_EVENT)
    assert char

    assert char.value is None

    service2 = acc.get_service(SERV_STATELESS_PROGRAMMABLE_SWITCH)
    assert service2
    char2 = service.get_characteristic(CHAR_PROGRAMMABLE_SWITCH_EVENT)
    assert char2
    broker = MagicMock()
    char2.broker = broker
    assert char2.value is None

    menuai.states.async_set(
        doorbell_entity_id,
        STATE_UNKNOWN,
        {ATTR_DEVICE_CLASS: EventDeviceClass.DOORBELL},
    )
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None
    assert len(broker.mock_calls) == 0

    char.set_value(True)
    char2.set_value(True)
    broker.reset_mock()

    original_time = dt_util.utcnow().isoformat()
    menuai.states.async_set(
        doorbell_entity_id,
        original_time,
        {ATTR_DEVICE_CLASS: EventDeviceClass.DOORBELL},
    )
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None
    assert len(broker.mock_calls) == 2
    broker.reset_mock()

    menuai.states.async_set(
        doorbell_entity_id,
        original_time,
        {ATTR_DEVICE_CLASS: EventDeviceClass.DOORBELL},
        force_update=True,
    )
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None
    assert len(broker.mock_calls) == 0
    broker.reset_mock()

    menuai.states.async_set(
        doorbell_entity_id,
        original_time,
        {ATTR_DEVICE_CLASS: EventDeviceClass.DOORBELL, "other": "attr"},
    )
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None
    assert len(broker.mock_calls) == 0
    broker.reset_mock()

    # Ensure we do not throw when the linked
    # doorbell sensor is removed
    menuai.states.async_remove(doorbell_entity_id)
    await menuai.async_block_till_done()
    acc.run()
    await menuai.async_block_till_done()
    assert char.value is None
    assert char2.value is None

    await menuai.async_block_till_done()
    menuai.states.async_set(
        doorbell_entity_id,
        STATE_UNAVAILABLE,
        {ATTR_DEVICE_CLASS: EventDeviceClass.DOORBELL},
    )
    await menuai.async_block_till_done()
    # Ensure re-adding does not fire an event
    assert not broker.mock_calls
    broker.reset_mock()

    # going from unavailable to a state should not fire an event
    menuai.states.async_set(
        doorbell_entity_id,
        dt_util.utcnow().isoformat(),
        {ATTR_DEVICE_CLASS: EventDeviceClass.DOORBELL},
    )
    await menuai.async_block_till_done()
    assert not broker.mock_calls

    # But a second update does
    menuai.states.async_set(
        doorbell_entity_id,
        dt_util.utcnow().isoformat(),
        {ATTR_DEVICE_CLASS: EventDeviceClass.DOORBELL},
    )
    await menuai.async_block_till_done()
    assert broker.mock_calls


async def test_camera_with_a_missing_linked_doorbell_sensor(
    menuai: menuai, run_driver
) -> None:
    """Test a camera with a configured linked doorbell sensor that is missing."""
    await async_setup_component(menuai, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        menuai, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )
    await menuai.async_block_till_done()
    doorbell_entity_id = "binary_sensor.doorbell"
    entity_id = "camera.demo_camera"
    menuai.states.async_set(entity_id, None)
    await menuai.async_block_till_done()
    acc = Camera(
        menuai,
        run_driver,
        "Camera",
        entity_id,
        2,
        {CONF_LINKED_DOORBELL_SENSOR: doorbell_entity_id},
    )
    bridge = HomeBridge("menuai", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    acc.run()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    assert not acc.get_service(SERV_DOORBELL)
    assert not acc.get_service(SERV_STATELESS_PROGRAMMABLE_SWITCH)
