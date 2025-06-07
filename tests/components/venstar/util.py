"""Tests for the venstar integration."""

import requests_mock

from menuai.components.climate import DOMAIN as CLIMATE_DOMAIN
from menuai.components.venstar.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PLATFORM
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import async_load_fixture

TEST_MODELS = ["t2k", "colortouch"]


def mock_venstar_devices(f):
    """Decorate function to mock a Venstar Colortouch and T2000 thermostat API."""

    async def wrapper(menuai: menuai) -> None:
        # Mock thermostats are:
        # Venstar T2000, FW 4.38
        # Venstar "colortouch" T7850, FW 5.1
        with requests_mock.mock() as m:
            for model in TEST_MODELS:
                m.get(
                    f"http://venstar-{model}.localdomain/",
                    text=await async_load_fixture(menuai, f"{model}_root.json", DOMAIN),
                )
                m.get(
                    f"http://venstar-{model}.localdomain/query/info",
                    text=await async_load_fixture(menuai, f"{model}_info.json", DOMAIN),
                )
                m.get(
                    f"http://venstar-{model}.localdomain/query/sensors",
                    text=await async_load_fixture(
                        menuai, f"{model}_sensors.json", DOMAIN
                    ),
                )
                m.get(
                    f"http://venstar-{model}.localdomain/query/alerts",
                    text=await async_load_fixture(menuai, f"{model}_alerts.json", DOMAIN),
                )
            await f(menuai)

    return wrapper


async def async_init_integration(
    menuai: menuai,
    skip_setup: bool = False,
):
    """Set up the venstar integration in MenuAI."""
    platform_config = [
        {
            CONF_PLATFORM: "venstar",
            CONF_HOST: f"venstar-{model}.localdomain",
        }
        for model in TEST_MODELS
    ]
    config = {CLIMATE_DOMAIN: platform_config}

    await async_setup_component(menuai, CLIMATE_DOMAIN, config)
    await menuai.async_block_till_done()
