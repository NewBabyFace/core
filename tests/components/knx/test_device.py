"""Test KNX devices."""

from typing import Any

from menuai.components.knx.const import DOMAIN
from menuai.components.knx.storage.config_store import (
    STORAGE_KEY as KNX_CONFIG_STORAGE_KEY,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

from .conftest import KNXTestKit

from tests.typing import WebSocketGenerator


async def test_create_device(
    menuai: menuai,
    knx: KNXTestKit,
    device_registry: dr.DeviceRegistry,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test device creation."""
    await knx.setup_integration()
    client = await menuai_ws_client(menuai)

    await client.send_json_auto_id(
        {
            "type": "knx/create_device",
            "name": "Test Device",
        }
    )
    res = await client.receive_json()
    assert res["success"], res
    assert res["result"]["name"] == "Test Device"
    assert res["result"]["manufacturer"] == "KNX"
    assert res["result"]["identifiers"]
    assert res["result"]["config_entries"][0] == knx.mock_config_entry.entry_id

    device_identifier = res["result"]["identifiers"][0][1]
    assert device_registry.async_get_device({(DOMAIN, device_identifier)})
    device_id = res["result"]["id"]
    assert device_registry.async_get(device_id)


async def test_remove_device(
    menuai: menuai,
    knx: KNXTestKit,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    menuai_ws_client: WebSocketGenerator,
    menuai_storage: dict[str, Any],
) -> None:
    """Test device removal."""
    assert await async_setup_component(menuai, "config", {})
    await knx.setup_integration(config_store_fixture="config_store_light_switch.json")
    client = await menuai_ws_client(menuai)

    await knx.assert_read("1/0/21", response=True, ignore_order=True)  # test light
    await knx.assert_read("1/0/45", response=True, ignore_order=True)  # test switch

    assert menuai_storage[KNX_CONFIG_STORAGE_KEY]["data"]["entities"].get("switch")
    test_device = device_registry.async_get_device(
        {(DOMAIN, "knx_vdev_4c80a564f5fe5da701ed293966d6384d")}
    )
    device_id = test_device.id
    device_entities = entity_registry.entities.get_entries_for_device_id(device_id)
    assert len(device_entities) == 1

    response = await client.remove_device(device_id, knx.mock_config_entry.entry_id)
    assert response["success"]
    assert not device_registry.async_get_device(
        {(DOMAIN, "knx_vdev_4c80a564f5fe5da701ed293966d6384d")}
    )
    assert not entity_registry.entities.get_entries_for_device_id(device_id)
    assert not menuai_storage[KNX_CONFIG_STORAGE_KEY]["data"]["entities"].get("switch")
