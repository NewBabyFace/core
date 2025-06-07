"""The test for the zodiac sensor platform."""

from datetime import datetime
from unittest.mock import patch

import pytest

from menuai.components.sensor import ATTR_OPTIONS, SensorDeviceClass
from menuai.components.zodiac.const import (
    ATTR_ELEMENT,
    ATTR_MODALITY,
    DOMAIN,
    ELEMENT_EARTH,
    ELEMENT_FIRE,
    ELEMENT_WATER,
    MODALITY_CARDINAL,
    MODALITY_FIXED,
    SIGN_ARIES,
    SIGN_SCORPIO,
    SIGN_TAURUS,
)
from menuai.const import ATTR_DEVICE_CLASS
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry

DAY1 = datetime(2020, 11, 15, tzinfo=dt_util.UTC)
DAY2 = datetime(2020, 4, 20, tzinfo=dt_util.UTC)
DAY3 = datetime(2020, 4, 21, tzinfo=dt_util.UTC)


@pytest.mark.parametrize(
    ("now", "sign", "element", "modality"),
    [
        (DAY1, SIGN_SCORPIO, ELEMENT_WATER, MODALITY_FIXED),
        (DAY2, SIGN_ARIES, ELEMENT_FIRE, MODALITY_CARDINAL),
        (DAY3, SIGN_TAURUS, ELEMENT_EARTH, MODALITY_FIXED),
    ],
)
async def test_zodiac_day(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    now: datetime,
    sign: str,
    element: str,
    modality: str,
) -> None:
    """Test the zodiac sensor."""
    await menuai.config.async_set_time_zone("UTC")
    MockConfigEntry(
        domain=DOMAIN,
    ).add_to_menuai(menuai)

    with patch("menuai.components.zodiac.sensor.utcnow", return_value=now):
        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.zodiac")
    assert state
    assert state.state == sign
    assert state.attributes
    assert state.attributes[ATTR_ELEMENT] == element
    assert state.attributes[ATTR_MODALITY] == modality
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.ENUM
    assert state.attributes[ATTR_OPTIONS] == [
        "aquarius",
        "aries",
        "cancer",
        "capricorn",
        "gemini",
        "leo",
        "libra",
        "pisces",
        "sagittarius",
        "scorpio",
        "taurus",
        "virgo",
    ]

    entry = entity_registry.async_get("sensor.zodiac")
    assert entry
    assert entry.unique_id == "zodiac"
    assert entry.translation_key == "sign"
