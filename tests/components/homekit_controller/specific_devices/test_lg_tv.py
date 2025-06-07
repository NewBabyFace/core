"""Test against characteristics captured from an LG TV."""

from menuai.components.media_player import (
    ATTR_INPUT_SOURCE_LIST,
    MediaPlayerEntityFeature,
)
from menuai.const import ATTR_SUPPORTED_FEATURES, STATE_ON
from menuai.core import menuai

from ..common import (
    HUB_TEST_ACCESSORY_ID,
    DeviceTestInfo,
    assert_devices_and_entities_created,
    setup_accessories_from_file,
    setup_test_accessories,
)


async def test_lg_tv_setup(menuai: menuai) -> None:
    """Test that a LG TV can be correctly setup in HA."""
    accessories = await setup_accessories_from_file(menuai, "lg_tv.json")
    await setup_test_accessories(menuai, accessories)

    await assert_devices_and_entities_created(
        menuai,
        DeviceTestInfo(
            unique_id=HUB_TEST_ACCESSORY_ID,
            name="LG webOS TV AF80",
            model="OLED55B9PUA",
            manufacturer="LG Electronics",
            sw_version="04.71.04",
            hw_version="1",
            serial_number="A0000A000000000A",
            devices=[],
            entities=[],
        ),
    )

    state = menuai.states.get("media_player.lg_webos_tv_af80")
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes[ATTR_INPUT_SOURCE_LIST] == [
        "AirPlay",
        "Live TV",
        "HDMI 1",
        "Sony",
        "Apple",
        "AV",
        "HDMI 4",
    ]
    features = state.attributes[ATTR_SUPPORTED_FEATURES]
    assert features & MediaPlayerEntityFeature.TURN_ON
    assert features & MediaPlayerEntityFeature.TURN_OFF
    assert features & MediaPlayerEntityFeature.SELECT_SOURCE
    assert features & MediaPlayerEntityFeature.PLAY
    assert features & MediaPlayerEntityFeature.PAUSE
