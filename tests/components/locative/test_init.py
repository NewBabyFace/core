"""The tests the for Locative device tracker platform."""

from http import HTTPStatus
from unittest.mock import patch

from aiohttp.test_utils import TestClient
import pytest

from menuai import config_entries
from menuai.components import locative
from menuai.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from menuai.components.device_tracker.legacy import Device
from menuai.components.locative import DOMAIN, TRACKER_UPDATE
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.dispatcher import DATA_DISPATCHER
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True)
def mock_dev_track(mock_device_tracker_conf: list[Device]) -> None:
    """Mock device tracker config loading."""


@pytest.fixture
async def locative_client(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> TestClient:
    """Locative mock client."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    with patch("menuai.components.device_tracker.legacy.update_config"):
        return await menuai_client()


@pytest.fixture
async def webhook_id(menuai: menuai, locative_client: TestClient) -> str:
    """Initialize the Geofency component and get the webhook_id."""
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:8123"},
    )
    result = await menuai.config_entries.flow.async_init(
        "locative", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM, result

    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await menuai.async_block_till_done()

    return result["result"].data["webhook_id"]


async def test_missing_data(locative_client: TestClient, webhook_id: str) -> None:
    """Test missing data."""
    url = f"/api/webhook/{webhook_id}"

    data = {
        "latitude": 1.0,
        "longitude": 1.1,
        "device": "123",
        "id": "Home",
        "trigger": "enter",
    }

    # No data
    req = await locative_client.post(url)
    assert req.status == HTTPStatus.UNPROCESSABLE_ENTITY

    # No latitude
    copy = data.copy()
    del copy["latitude"]
    req = await locative_client.post(url, data=copy)
    assert req.status == HTTPStatus.UNPROCESSABLE_ENTITY

    # No device
    copy = data.copy()
    del copy["device"]
    req = await locative_client.post(url, data=copy)
    assert req.status == HTTPStatus.UNPROCESSABLE_ENTITY

    # No location
    copy = data.copy()
    del copy["id"]
    req = await locative_client.post(url, data=copy)
    assert req.status == HTTPStatus.UNPROCESSABLE_ENTITY

    # No trigger
    copy = data.copy()
    del copy["trigger"]
    req = await locative_client.post(url, data=copy)
    assert req.status == HTTPStatus.UNPROCESSABLE_ENTITY

    # Test message
    copy = data.copy()
    copy["trigger"] = "test"
    req = await locative_client.post(url, data=copy)
    assert req.status == HTTPStatus.OK

    # Test message, no location
    copy = data.copy()
    copy["trigger"] = "test"
    del copy["id"]
    req = await locative_client.post(url, data=copy)
    assert req.status == HTTPStatus.OK

    # Unknown trigger
    copy = data.copy()
    copy["trigger"] = "foobar"
    req = await locative_client.post(url, data=copy)
    assert req.status == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_enter_and_exit(
    menuai: menuai, locative_client: TestClient, webhook_id: str
) -> None:
    """Test when there is a known zone."""
    url = f"/api/webhook/{webhook_id}"

    data = {
        "latitude": 40.7855,
        "longitude": -111.7367,
        "device": "123",
        "id": "Home",
        "trigger": "enter",
    }

    # Enter the Home
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state_name = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}").state
    assert state_name == "home"

    data["id"] = "HOME"
    data["trigger"] = "exit"

    # Exit Home
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state_name = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}").state
    assert state_name == "not_home"

    data["id"] = "hOmE"
    data["trigger"] = "enter"

    # Enter Home again
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state_name = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}").state
    assert state_name == "home"

    data["trigger"] = "exit"

    # Exit Home
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state_name = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}").state
    assert state_name == "not_home"

    data["id"] = "work"
    data["trigger"] = "enter"

    # Enter Work
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK
    state_name = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}").state
    assert state_name == "work"


async def test_exit_after_enter(
    menuai: menuai, locative_client: TestClient, webhook_id: str
) -> None:
    """Test when an exit message comes after an enter message."""
    url = f"/api/webhook/{webhook_id}"

    data = {
        "latitude": 40.7855,
        "longitude": -111.7367,
        "device": "123",
        "id": "Home",
        "trigger": "enter",
    }

    # Enter Home
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK

    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}")
    assert state.state == "home"

    data["id"] = "Work"

    # Enter Work
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK

    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}")
    assert state.state == "work"

    data["id"] = "Home"
    data["trigger"] = "exit"

    # Exit Home
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK

    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}")
    assert state.state == "work"


async def test_exit_first(
    menuai: menuai, locative_client: TestClient, webhook_id: str
) -> None:
    """Test when an exit message is sent first on a new device."""
    url = f"/api/webhook/{webhook_id}"

    data = {
        "latitude": 40.7855,
        "longitude": -111.7367,
        "device": "new_device",
        "id": "Home",
        "trigger": "exit",
    }

    # Exit Home
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK

    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}")
    assert state.state == "not_home"


async def test_two_devices(
    menuai: menuai, locative_client: TestClient, webhook_id: str
) -> None:
    """Test updating two different devices."""
    url = f"/api/webhook/{webhook_id}"

    data_device_1 = {
        "latitude": 40.7855,
        "longitude": -111.7367,
        "device": "device_1",
        "id": "Home",
        "trigger": "exit",
    }

    # Exit Home
    req = await locative_client.post(url, data=data_device_1)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK

    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data_device_1['device']}")
    assert state.state == "not_home"

    # Enter Home
    data_device_2 = dict(data_device_1)
    data_device_2["device"] = "device_2"
    data_device_2["trigger"] = "enter"
    req = await locative_client.post(url, data=data_device_2)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK

    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data_device_2['device']}")
    assert state.state == "home"
    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data_device_1['device']}")
    assert state.state == "not_home"


@pytest.mark.xfail(
    reason="The device_tracker component does not support unloading yet."
)
async def test_load_unload_entry(
    menuai: menuai, locative_client: TestClient, webhook_id: str
) -> None:
    """Test that the appropriate dispatch signals are added and removed."""
    url = f"/api/webhook/{webhook_id}"

    data = {
        "latitude": 40.7855,
        "longitude": -111.7367,
        "device": "new_device",
        "id": "Home",
        "trigger": "exit",
    }

    # Exit Home
    req = await locative_client.post(url, data=data)
    await menuai.async_block_till_done()
    assert req.status == HTTPStatus.OK

    state = menuai.states.get(f"{DEVICE_TRACKER_DOMAIN}.{data['device']}")
    assert state.state == "not_home"
    assert len(menuai.data[DATA_DISPATCHER][TRACKER_UPDATE]) == 1

    entry = menuai.config_entries.async_entries(DOMAIN)[0]

    await locative.async_unload_entry(menuai, entry)
    await menuai.async_block_till_done()
    assert not menuai.data[DATA_DISPATCHER][TRACKER_UPDATE]
