"""Test the Smart Meter Texas sensor entity."""

from unittest.mock import patch

from menuai.components.menuai import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.components.smart_meter_texas.const import (
    ELECTRIC_METER,
    ESIID,
    METER_NUMBER,
)
from menuai.const import ATTR_ENTITY_ID, CONF_ADDRESS
from menuai.core import menuai
from menuai.setup import async_setup_component

from .conftest import TEST_ENTITY_ID, refresh_data, setup_integration

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_sensor(
    menuai: menuai, config_entry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that the sensor is setup."""
    await setup_integration(menuai, config_entry, aioclient_mock)
    await refresh_data(menuai, config_entry, aioclient_mock)
    meter = menuai.states.get(TEST_ENTITY_ID)

    assert meter
    assert meter.state == "9751.212"


async def test_name(
    menuai: menuai, config_entry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test sensor name property."""
    await setup_integration(menuai, config_entry, aioclient_mock)
    await refresh_data(menuai, config_entry, aioclient_mock)
    meter = menuai.states.get(TEST_ENTITY_ID)

    assert meter.name == f"{ELECTRIC_METER} 123456789"


async def test_attributes(
    menuai: menuai, config_entry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test meter attributes."""
    await setup_integration(menuai, config_entry, aioclient_mock)
    await refresh_data(menuai, config_entry, aioclient_mock)
    meter = menuai.states.get(TEST_ENTITY_ID)

    assert meter.attributes[METER_NUMBER] == "123456789"
    assert meter.attributes[ESIID] == "12345678901234567"
    assert meter.attributes[CONF_ADDRESS] == "123 MAIN ST"


async def test_generic_entity_update_service(
    menuai: menuai, config_entry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test generic update entity service homeasasistant/update_entity."""
    await setup_integration(menuai, config_entry, aioclient_mock)
    await async_setup_component(menuai, HA_DOMAIN, {})
    with patch("smart_meter_texas.Meter.read_meter") as updater:
        await menuai.services.async_call(
            HA_DOMAIN,
            SERVICE_UPDATE_ENTITY,
            {ATTR_ENTITY_ID: TEST_ENTITY_ID},
            blocking=True,
        )
        await menuai.async_block_till_done()
        updater.assert_called_once()
