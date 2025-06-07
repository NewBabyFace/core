"""Test configuration and mocks for Smart Meter Texas."""

from http import HTTPStatus
import json
from typing import Any

import pytest
from smart_meter_texas.const import (
    AUTH_ENDPOINT,
    BASE_ENDPOINT,
    BASE_URL,
    LATEST_OD_READ_ENDPOINT,
    METER_ENDPOINT,
    OD_READ_ENDPOINT,
)

from menuai.components.menuai import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.components.smart_meter_texas.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

TEST_ENTITY_ID = "sensor.electric_meter_123456789"


def load_smt_fixture(name):
    """Return a dict of the json fixture."""
    json_fixture = load_fixture(f"{name}.json", DOMAIN)
    return json.loads(json_fixture)


async def setup_integration(
    menuai: menuai,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    **kwargs: Any,
) -> None:
    """Initialize the Smart Meter Texas integration for testing."""
    mock_connection(aioclient_mock, **kwargs)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()


async def refresh_data(
    menuai: menuai,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Request a DataUpdateCoordinator refresh."""
    mock_connection(aioclient_mock)
    await async_setup_component(menuai, HA_DOMAIN, {})
    await menuai.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
        blocking=True,
    )
    await menuai.async_block_till_done()


def mock_connection(
    aioclient_mock, auth_fail=False, auth_timeout=False, bad_reading=False
):
    """Mock all calls to the API."""
    aioclient_mock.get(BASE_URL)

    auth_endpoint = AUTH_ENDPOINT
    if not auth_fail and not auth_timeout:
        aioclient_mock.post(
            auth_endpoint,
            json={"token": "token123"},
        )
    elif auth_fail:
        aioclient_mock.post(
            auth_endpoint,
            status=HTTPStatus.BAD_REQUEST,
            json={"errormessage": "ERR-USR-INVALIDPASSWORDERROR"},
        )
    else:  # auth_timeout
        aioclient_mock.post(auth_endpoint, exc=TimeoutError)

    aioclient_mock.post(
        f"{BASE_ENDPOINT}{METER_ENDPOINT}",
        json=load_smt_fixture("meter"),
    )
    aioclient_mock.post(f"{BASE_ENDPOINT}{OD_READ_ENDPOINT}", json={"data": None})
    if not bad_reading:
        aioclient_mock.post(
            f"{BASE_ENDPOINT}{LATEST_OD_READ_ENDPOINT}",
            json=load_smt_fixture("latestodrread"),
        )
    else:
        aioclient_mock.post(
            f"{BASE_ENDPOINT}{LATEST_OD_READ_ENDPOINT}",
            json={},
        )


@pytest.fixture(name="config_entry")
def mock_config_entry(menuai: menuai) -> MockConfigEntry:
    """Return a mock config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="user123",
        data={"username": "user123", "password": "password123"},
    )
    config_entry.add_to_menuai(menuai)

    return config_entry
