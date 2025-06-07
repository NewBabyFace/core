"""The image tests for the AEMET OpenData platform."""

from freezegun.api import FrozenDateTimeFactory

from menuai.core import menuai

from .util import async_init_integration


async def test_aemet_create_images(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test creation of AEMET images."""

    await menuai.config.async_set_time_zone("UTC")
    freezer.move_to("2021-01-09 12:00:00+00:00")
    await async_init_integration(menuai)

    state = menuai.states.get("image.aemet_weather_radar")
    assert state is not None
    assert state.state == "2021-01-09T11:34:06.448809+00:00"
