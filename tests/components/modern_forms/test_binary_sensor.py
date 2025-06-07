"""Tests for the Modern Forms sensor platform."""

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.components.modern_forms.const import DOMAIN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_binary_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test the creation and values of the Modern Forms sensors."""

    entity_registry.async_get_or_create(
        BINARY_SENSOR_DOMAIN,
        DOMAIN,
        "AA:BB:CC:DD:EE:FF_light_sleep_timer_active",
        suggested_object_id="modernformsfan_light_sleep_timer_active",
        disabled_by=None,
    )
    entity_registry.async_get_or_create(
        BINARY_SENSOR_DOMAIN,
        DOMAIN,
        "AA:BB:CC:DD:EE:FF_fan_sleep_timer_active",
        suggested_object_id="modernformsfan_fan_sleep_timer_active",
        disabled_by=None,
    )

    await init_integration(menuai, aioclient_mock)

    # Light timer remaining time
    state = menuai.states.get("binary_sensor.modernformsfan_light_sleep_timer_active")
    assert state
    assert state.state == "off"

    # Fan timer remaining time
    state = menuai.states.get("binary_sensor.modernformsfan_fan_sleep_timer_active")
    assert state
    assert state.state == "off"
