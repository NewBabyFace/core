"""Conftest for rainforest_eagle."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from menuai.components.rainforest_eagle.const import (
    CONF_CLOUD_ID,
    CONF_HARDWARE_ADDRESS,
    CONF_INSTALL_CODE,
    DOMAIN,
    TYPE_EAGLE_100,
    TYPE_EAGLE_200,
)
from menuai.const import CONF_HOST, CONF_TYPE
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import MOCK_200_RESPONSE_WITHOUT_PRICE, MOCK_CLOUD_ID

from tests.common import MockConfigEntry


@pytest.fixture
def config_entry_200(menuai: menuai) -> MockConfigEntry:
    """Return a config entry."""
    entry = MockConfigEntry(
        domain="rainforest_eagle",
        data={
            CONF_CLOUD_ID: MOCK_CLOUD_ID,
            CONF_HOST: "192.168.1.55",
            CONF_INSTALL_CODE: "abcdefgh",
            CONF_HARDWARE_ADDRESS: "mock-hw-address",
            CONF_TYPE: TYPE_EAGLE_200,
        },
    )
    entry.add_to_menuai(menuai)
    return entry


@pytest.fixture
async def setup_rainforest_200(
    menuai: menuai, config_entry_200: MockConfigEntry
) -> AsyncGenerator[Mock]:
    """Set up rainforest."""
    with patch(
        "aioeagle.ElectricMeter.create_instance",
        return_value=Mock(
            get_device_query=AsyncMock(return_value=MOCK_200_RESPONSE_WITHOUT_PRICE)
        ),
    ) as mock_update:
        mock_update.return_value.is_connected = True
        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()
        yield mock_update.return_value


@pytest.fixture
async def setup_rainforest_100(menuai: menuai) -> AsyncGenerator[MagicMock]:
    """Set up rainforest."""
    MockConfigEntry(
        domain="rainforest_eagle",
        data={
            CONF_CLOUD_ID: MOCK_CLOUD_ID,
            CONF_HOST: "192.168.1.55",
            CONF_INSTALL_CODE: "abcdefgh",
            CONF_HARDWARE_ADDRESS: None,
            CONF_TYPE: TYPE_EAGLE_100,
        },
    ).add_to_menuai(menuai)
    with patch(
        "menuai.components.rainforest_eagle.coordinator.Eagle100Reader",
        return_value=Mock(
            get_instantaneous_demand=Mock(
                return_value={"InstantaneousDemand": {"Demand": "1.152000"}}
            ),
            get_current_summation=Mock(
                return_value={
                    "CurrentSummation": {
                        "SummationDelivered": "45251.285000",
                        "SummationReceived": "232.232000",
                    }
                }
            ),
        ),
    ) as mock_update:
        assert await async_setup_component(menuai, DOMAIN, {})
        await menuai.async_block_till_done()
        yield mock_update
