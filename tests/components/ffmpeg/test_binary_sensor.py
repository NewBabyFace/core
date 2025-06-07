"""The tests for MenuAI ffmpeg binary sensor."""

from unittest.mock import AsyncMock, patch

from menuai.const import EVENT_menuai_START
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import assert_setup_component

CONFIG_NOISE = {
    "binary_sensor": {"platform": "ffmpeg_noise", "input": "testinputvideo"}
}
CONFIG_MOTION = {
    "binary_sensor": {"platform": "ffmpeg_motion", "input": "testinputvideo"}
}


# -- ffmpeg noise binary_sensor --


async def test_noise_setup_component(menuai: menuai) -> None:
    """Set up ffmpeg component."""
    with assert_setup_component(1, "binary_sensor"):
        await async_setup_component(menuai, "binary_sensor", CONFIG_NOISE)
    await menuai.async_block_till_done()

    assert menuai.data["ffmpeg"].binary == "ffmpeg"
    assert menuai.states.get("binary_sensor.ffmpeg_noise") is not None


@patch("haffmpeg.sensor.SensorNoise.open_sensor", side_effect=AsyncMock())
async def test_noise_setup_component_start(mock_start, menuai: menuai) -> None:
    """Set up ffmpeg component."""
    with assert_setup_component(1, "binary_sensor"):
        await async_setup_component(menuai, "binary_sensor", CONFIG_NOISE)
    await menuai.async_block_till_done()

    assert menuai.data["ffmpeg"].binary == "ffmpeg"
    assert menuai.states.get("binary_sensor.ffmpeg_noise") is not None

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert mock_start.called

    entity = menuai.states.get("binary_sensor.ffmpeg_noise")
    assert entity.state == "unavailable"


@patch("haffmpeg.sensor.SensorNoise")
async def test_noise_setup_component_start_callback(
    mock_ffmpeg, menuai: menuai
) -> None:
    """Set up ffmpeg component."""
    mock_ffmpeg().open_sensor.side_effect = AsyncMock()
    mock_ffmpeg().close = AsyncMock()
    with assert_setup_component(1, "binary_sensor"):
        await async_setup_component(menuai, "binary_sensor", CONFIG_NOISE)
    await menuai.async_block_till_done()

    assert menuai.data["ffmpeg"].binary == "ffmpeg"
    assert menuai.states.get("binary_sensor.ffmpeg_noise") is not None

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()

    entity = menuai.states.get("binary_sensor.ffmpeg_noise")
    assert entity.state == "off"

    mock_ffmpeg.call_args[0][1](True)
    await menuai.async_block_till_done()

    entity = menuai.states.get("binary_sensor.ffmpeg_noise")
    assert entity.state == "on"


# -- ffmpeg motion binary_sensor --


async def test_motion_setup_component(menuai: menuai) -> None:
    """Set up ffmpeg component."""
    with assert_setup_component(1, "binary_sensor"):
        await async_setup_component(menuai, "binary_sensor", CONFIG_MOTION)
    await menuai.async_block_till_done()

    assert menuai.data["ffmpeg"].binary == "ffmpeg"
    assert menuai.states.get("binary_sensor.ffmpeg_motion") is not None


@patch("haffmpeg.sensor.SensorMotion.open_sensor", side_effect=AsyncMock())
async def test_motion_setup_component_start(mock_start, menuai: menuai) -> None:
    """Set up ffmpeg component."""
    with assert_setup_component(1, "binary_sensor"):
        await async_setup_component(menuai, "binary_sensor", CONFIG_MOTION)
    await menuai.async_block_till_done()

    assert menuai.data["ffmpeg"].binary == "ffmpeg"
    assert menuai.states.get("binary_sensor.ffmpeg_motion") is not None

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    assert mock_start.called

    entity = menuai.states.get("binary_sensor.ffmpeg_motion")
    assert entity.state == "unavailable"


@patch("haffmpeg.sensor.SensorMotion")
async def test_motion_setup_component_start_callback(
    mock_ffmpeg, menuai: menuai
) -> None:
    """Set up ffmpeg component."""
    mock_ffmpeg().open_sensor.side_effect = AsyncMock()
    mock_ffmpeg().close = AsyncMock()
    with assert_setup_component(1, "binary_sensor"):
        await async_setup_component(menuai, "binary_sensor", CONFIG_MOTION)
    await menuai.async_block_till_done()

    assert menuai.data["ffmpeg"].binary == "ffmpeg"
    assert menuai.states.get("binary_sensor.ffmpeg_motion") is not None

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()

    entity = menuai.states.get("binary_sensor.ffmpeg_motion")
    assert entity.state == "off"

    mock_ffmpeg.call_args[0][1](True)
    await menuai.async_block_till_done()

    entity = menuai.states.get("binary_sensor.ffmpeg_motion")
    assert entity.state == "on"
