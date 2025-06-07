"""The tests the for GPSLogger device tracker platform."""

from http import HTTPStatus
from unittest.mock import patch

from aiohttp.test_utils import TestClient
import pytest

from menuai import config_entries
from menuai.components import gpslogger, zone
from menuai.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from menuai.components.device_tracker.legacy import Device
from menuai.components.gpslogger import DOMAIN, TRACKER_UPDATE
from menuai.const import STATE_HOME, STATE_NOT_HOME
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.dispatcher import DATA_DISPATCHER
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator

HOME_LATITUDE = 37.239622
HOME_LONGITUDE = -115.815811


@pytest.fixture(autouse=True)
def mock_dev_track(mock_device_tracker_conf: list[Device]) -> None:
    """Mock device tracker config loading."""


@pytest.fixture
async def gpslogger_client(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> TestClient:
    """Mock client for GPSLogger (unauthenticated)."""

    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    await menuai.async_block_till_done()

    with patch("menuai.components.device_tracker.legacy.update_config"):
        return await menuai_client_no_auth()


@pytest.fixture(autouse=True)
async def setup_zones(menuai: menuai) -> None:
    """Set up Zone config in HA."""
    assert await async_setup_component(
        menuai,
        zone.DOMAIN,
        {
            "zone": {
                "name": "Home",
                "latitude": HOME_LATITUDE,
                "longitude": HOME_LONGITUDE,
                "radius": 100,
            }
        },
    )
    await menuai.async_block_till_done()


@pytest.fixture
async def webhook_id(menuai: menuai, gpslogger_client: TestClient) -> str:
    """Initialize the GPSLogger component and get the webhook_id."""
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:8123"},
    )
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM, result

    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY

    await menuai.async_block_till_done()
    return result["result"].data["webhook_id"]


async def test_missing_data(
    menuai: menuai, gpslogger_client: TestClient, webhook_id: str
) -> None:
    """Test missing data."""
    url = f"/api/webhook/{webhook_id}"

    data = {"latitude": 1.0, "longitude": 1.1, "device": "123"}

    # No data
    req = await gpslogger_client.post(url)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.UNPROCESSABLE_ENTITY

    # No latitude
    copy = data.copy()
    del copy["latitude"]
    req = await gpslogger_client.post(url, data=copy)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.UNPROCESSABLE_ENTITY

    # No device
    copy = data.copy()
    del copy["device"]
    req = await gpslogger_client.post(url, data=copy)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_enter_and_exit(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    gpslogger_client: TestClient,
    webhook_id: str,
) -> None:
    """Test when there is a known zone."""
    url = f"/api/webhook/{webhook_id}"

    data = {"latitude": HOME_LATITUDE, "longitude": HOME_LONGITUDE, "device": "123"}

    # Enter the Home
    req = await gpslogger_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state_name = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}").state
    assert state_name == STATE_HOME

    # Enter Home again
    req = await gpslogger_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state_name = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}").state
    assert state_name == STATE_HOME

    data["longitude"] = 0
    data["latitude"] = 0

    # Enter Somewhere else
    req = await gpslogger_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state_name = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}").state
    assert state_name == STATE_NOT_HOME

    assert len(device_registry.devices) == 1
    assert len(entity_registry.entities) == 1


async def test_enter_with_attrs(
    menuai: menuai, gpslogger_client: TestClient, webhook_id: str
) -> None:
    """Test when additional attributes are present."""
    url = f"/api/webhook/{webhook_id}"

    data = {
        "latitude": 1.0,
        "longitude": 1.1,
        "device": "123",
        "accuracy": 10.5,
        "battery": 10,
        "speed": 100,
        "direction": 105.32,
        "altitude": 102,
        "provider": "gps",
        "activity": "running",
    }

    req = await gpslogger_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}")
    assert state.state == STATE_NOT_HOME
    assert state.attributes["gps_accuracy"] == 10.5
    assert state.attributes["battery_level"] == 10.0
    assert state.attributes["speed"] == 100.0
    assert state.attributes["direction"] == 105.32
    assert state.attributes["altitude"] == 102.0
    assert state.attributes["provider"] == "gps"
    assert state.attributes["activity"] == "running"

    data = {
        "latitude": HOME_LATITUDE,
        "longitude": HOME_LONGITUDE,
        "device": "123",
        "accuracy": 123,
        "battery": 23,
        "speed": 23,
        "direction": 123,
        "altitude": 123,
        "provider": "gps",
        "activity": "idle",
    }

    req = await gpslogger_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}")
    assert state.state == STATE_HOME
    assert state.attributes["gps_accuracy"] == 123
    assert state.attributes["battery_level"] == 23
    assert state.attributes["speed"] == 23
    assert state.attributes["direction"] == 123
    assert state.attributes["altitude"] == 123
    assert state.attributes["provider"] == "gps"
    assert state.attributes["activity"] == "idle"


@pytest.mark.xfail(
    reason="The device_tracker component does not support unloading yet."
)
async def test_load_unload_entry(
    menuai: menuai, gpslogger_client: TestClient, webhook_id: str
) -> None:
    """Test that the appropriate dispatch signals are added and removed."""
    url = f"/api/webhook/{webhook_id}"
    data = {"latitude": HOME_LATITUDE, "longitude": HOME_LONGITUDE, "device": "123"}

    # Enter the Home
    req = await gpslogger_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state_name = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}").state
    assert state_name == STATE_HOME
    assert len(menuai.data[DATA_DISPATCHER][TRACKER_UPDATE]) == 1

    entry = menuai.config_entries.async_entries(DOMAIN)[0]

    assert await gpslogger.async_unload_entry(menuai, entry)
    await menuai.async_block_till_done()
    assert not menuai.data[DATA_DISPATCHER][TRACKER_UPDATE]
