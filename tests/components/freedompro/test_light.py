"""Tests for the Freedompro light."""

from unittest.mock import patch

import pytest

from menuai.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def mock_freedompro_put_state():
    """Mock freedompro put_state."""
    with patch("menuai.components.freedompro.light.put_state"):
        yield


async def test_light_get_state(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test states of the light."""

    entity_id = "light.lightbulb"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON
    assert state.attributes.get("friendly_name") == "lightbulb"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert (
        entry.unique_id
        == "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*JHJZIZ9ORJNHB7DZNBNAOSEDECVTTZ48SABTCA3WA3M"
    )


async def test_light_set_on(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test set on of the light."""

    entity_id = "light.lightbulb"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON
    assert state.attributes.get("friendly_name") == "lightbulb"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert (
        entry.unique_id
        == "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*JHJZIZ9ORJNHB7DZNBNAOSEDECVTTZ48SABTCA3WA3M"
    )

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON


async def test_light_set_off(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test set off of the light."""

    entity_id = "light.bedroomlight"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes.get("friendly_name") == "bedroomlight"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert (
        entry.unique_id
        == "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*3-QURR5Q6ADA8ML1TBRG59RRGM1F9LVUZLKPYKFJQHC"
    )

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF


async def test_light_set_brightness(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test set brightness of the light."""

    entity_id = "light.lightbulb"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON
    assert state.attributes.get("friendly_name") == "lightbulb"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert (
        entry.unique_id
        == "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*JHJZIZ9ORJNHB7DZNBNAOSEDECVTTZ48SABTCA3WA3M"
    )

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [entity_id], ATTR_BRIGHTNESS: 255},
        blocking=True,
    )

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON
    assert int(state.attributes[ATTR_BRIGHTNESS]) == 0


async def test_light_set_hue(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test set brightness of the light."""

    entity_id = "light.lightbulb"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON
    assert state.attributes.get("friendly_name") == "lightbulb"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert (
        entry.unique_id
        == "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*JHJZIZ9ORJNHB7DZNBNAOSEDECVTTZ48SABTCA3WA3M"
    )

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: [entity_id],
            ATTR_BRIGHTNESS: 255,
            ATTR_HS_COLOR: (352.32, 100.0),
        },
        blocking=True,
    )

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON
    assert int(state.attributes[ATTR_BRIGHTNESS]) == 0
    assert state.attributes[ATTR_HS_COLOR] == (0, 0)
