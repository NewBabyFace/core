"""deCONZ service tests."""

from collections.abc import Callable
from typing import Any

import pytest
import voluptuous as vol

from menuai.components.deconz.const import (
    CONF_BRIDGE_ID,
    CONF_MASTER_GATEWAY,
    DOMAIN,
)
from menuai.components.deconz.deconz_event import CONF_DECONZ_EVENT
from menuai.components.deconz.services import (
    SERVICE_CONFIGURE_DEVICE,
    SERVICE_DATA,
    SERVICE_DEVICE_REFRESH,
    SERVICE_ENTITY,
    SERVICE_FIELD,
    SERVICE_REMOVE_ORPHANED_ENTRIES,
)
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from .test_hub import BRIDGE_ID

from tests.common import MockConfigEntry, async_capture_events
from tests.test_util.aiohttp import AiohttpClientMocker


@pytest.mark.usefixtures("config_entry_setup")
async def test_configure_service_with_field(
    menuai: menuai,
    mock_put_request: Callable[[str, str], AiohttpClientMocker],
) -> None:
    """Test that service invokes pydeconz with the correct path and data."""
    data = {
        SERVICE_FIELD: "/lights/2",
        CONF_BRIDGE_ID: BRIDGE_ID,
        SERVICE_DATA: {"on": True, "attr1": 10, "attr2": 20},
    }

    aioclient_mock = mock_put_request("/lights/2")

    await menuai.services.async_call(
        DOMAIN, SERVICE_CONFIGURE_DEVICE, service_data=data, blocking=True
    )
    assert aioclient_mock.mock_calls[1][2] == {"on": True, "attr1": 10, "attr2": 20}


@pytest.mark.parametrize(
    "light_payload",
    [
        {
            "name": "Test",
            "state": {"reachable": True},
            "type": "Light",
            "uniqueid": "00:00:00:00:00:00:00:01-00",
        }
    ],
)
@pytest.mark.usefixtures("config_entry_setup")
async def test_configure_service_with_entity(
    menuai: menuai,
    mock_put_request: Callable[[str, str], AiohttpClientMocker],
) -> None:
    """Test that service invokes pydeconz with the correct path and data."""
    data = {
        SERVICE_ENTITY: "light.test",
        SERVICE_DATA: {"on": True, "attr1": 10, "attr2": 20},
    }
    aioclient_mock = mock_put_request("/lights/0")

    await menuai.services.async_call(
        DOMAIN, SERVICE_CONFIGURE_DEVICE, service_data=data, blocking=True
    )
    assert aioclient_mock.mock_calls[1][2] == {"on": True, "attr1": 10, "attr2": 20}


@pytest.mark.parametrize(
    "light_payload",
    [
        {
            "name": "Test",
            "state": {"reachable": True},
            "type": "Light",
            "uniqueid": "00:00:00:00:00:00:00:01-00",
        }
    ],
)
@pytest.mark.usefixtures("config_entry_setup")
async def test_configure_service_with_entity_and_field(
    menuai: menuai,
    mock_put_request: Callable[[str, str], AiohttpClientMocker],
) -> None:
    """Test that service invokes pydeconz with the correct path and data."""
    data = {
        SERVICE_ENTITY: "light.test",
        SERVICE_FIELD: "/state",
        SERVICE_DATA: {"on": True, "attr1": 10, "attr2": 20},
    }
    aioclient_mock = mock_put_request("/lights/0/state")

    await menuai.services.async_call(
        DOMAIN, SERVICE_CONFIGURE_DEVICE, service_data=data, blocking=True
    )
    assert aioclient_mock.mock_calls[1][2] == {"on": True, "attr1": 10, "attr2": 20}


@pytest.mark.usefixtures("config_entry_setup")
async def test_configure_service_with_faulty_bridgeid(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that service fails on a bad bridge id."""
    aioclient_mock.clear_requests()

    data = {
        CONF_BRIDGE_ID: "Bad bridge id",
        SERVICE_FIELD: "/lights/1",
        SERVICE_DATA: {"on": True},
    }

    await menuai.services.async_call(DOMAIN, SERVICE_CONFIGURE_DEVICE, service_data=data)
    await menuai.async_block_till_done()

    assert len(aioclient_mock.mock_calls) == 0


@pytest.mark.usefixtures("config_entry_setup")
async def test_configure_service_with_faulty_field(menuai: menuai) -> None:
    """Test that service fails on a bad field."""
    data = {SERVICE_FIELD: "light/2", SERVICE_DATA: {}}

    with pytest.raises(vol.Invalid):
        await menuai.services.async_call(
            DOMAIN, SERVICE_CONFIGURE_DEVICE, service_data=data
        )


@pytest.mark.usefixtures("config_entry_setup")
async def test_configure_service_with_faulty_entity(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that service on a non existing entity."""
    aioclient_mock.clear_requests()

    data = {
        SERVICE_ENTITY: "light.nonexisting",
        SERVICE_DATA: {},
    }

    await menuai.services.async_call(DOMAIN, SERVICE_CONFIGURE_DEVICE, service_data=data)
    await menuai.async_block_till_done()

    assert len(aioclient_mock.mock_calls) == 0


@pytest.mark.parametrize("config_entry_options", [{CONF_MASTER_GATEWAY: False}])
@pytest.mark.usefixtures("config_entry_setup")
async def test_calling_service_with_no_master_gateway_fails(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that service call fails when no master gateway exist."""
    aioclient_mock.clear_requests()

    data = {
        SERVICE_FIELD: "/lights/1",
        SERVICE_DATA: {"on": True},
    }

    await menuai.services.async_call(DOMAIN, SERVICE_CONFIGURE_DEVICE, service_data=data)
    await menuai.async_block_till_done()

    assert len(aioclient_mock.mock_calls) == 0


@pytest.mark.usefixtures("config_entry_setup")
async def test_service_refresh_devices(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    deconz_payload: dict[str, Any],
    mock_requests: Callable[[], None],
) -> None:
    """Test that service can refresh devices."""
    assert len(menuai.states.async_all()) == 0

    aioclient_mock.clear_requests()

    deconz_payload |= {
        "groups": {
            "1": {
                "id": "Group 1 id",
                "name": "Group 1 name",
                "type": "LightGroup",
                "state": {},
                "action": {},
                "scenes": [{"id": "1", "name": "Scene 1"}],
                "lights": ["1"],
            }
        },
        "lights": {
            "1": {
                "name": "Light 1 name",
                "state": {"reachable": True},
                "type": "Light",
                "uniqueid": "00:00:00:00:00:00:00:01-00",
            }
        },
        "sensors": {
            "1": {
                "name": "Sensor 1 name",
                "type": "ZHALightLevel",
                "state": {"lightlevel": 30000, "dark": False},
                "config": {"reachable": True},
                "uniqueid": "00:00:00:00:00:00:00:02-00",
            }
        },
    }
    mock_requests()

    await menuai.services.async_call(
        DOMAIN, SERVICE_DEVICE_REFRESH, service_data={CONF_BRIDGE_ID: BRIDGE_ID}
    )
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 5


@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "name": "Switch 1",
            "type": "ZHASwitch",
            "state": {"buttonevent": 1000},
            "config": {"battery": 100},
            "uniqueid": "00:00:00:00:00:00:00:01-00",
        }
    ],
)
@pytest.mark.usefixtures("config_entry_setup")
async def test_service_refresh_devices_trigger_no_state_update(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    deconz_payload: dict[str, Any],
    mock_requests,
) -> None:
    """Verify that gateway.ignore_state_updates are honored."""
    assert len(menuai.states.async_all()) == 1

    captured_events = async_capture_events(menuai, CONF_DECONZ_EVENT)

    aioclient_mock.clear_requests()

    deconz_payload |= {
        "groups": {
            "1": {
                "id": "Group 1 id",
                "name": "Group 1 name",
                "type": "LightGroup",
                "state": {},
                "action": {},
                "scenes": [{"id": "1", "name": "Scene 1"}],
                "lights": ["1"],
            }
        },
        "lights": {
            "1": {
                "name": "Light 1 name",
                "state": {"reachable": True},
                "type": "Light",
                "uniqueid": "00:00:00:00:00:00:00:01-00",
            }
        },
        "sensors": {
            "0": {
                "name": "Switch 1",
                "type": "ZHASwitch",
                "state": {"buttonevent": 1000},
                "config": {"battery": 100},
                "uniqueid": "00:00:00:00:00:00:00:01-00",
            }
        },
    }
    mock_requests()

    await menuai.services.async_call(
        DOMAIN, SERVICE_DEVICE_REFRESH, service_data={CONF_BRIDGE_ID: BRIDGE_ID}
    )
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 5
    assert len(captured_events) == 0


@pytest.mark.parametrize(
    "light_payload",
    [
        {
            "name": "Light 0 name",
            "state": {"reachable": True},
            "type": "Light",
            "uniqueid": "00:00:00:00:00:00:00:01-00",
        }
    ],
)
@pytest.mark.parametrize(
    "sensor_payload",
    [
        {
            "name": "Switch 1",
            "type": "ZHASwitch",
            "state": {"buttonevent": 1000, "gesture": 1},
            "config": {"battery": 100},
            "uniqueid": "00:00:00:00:00:00:00:03-00",
        }
    ],
)
async def test_remove_orphaned_entries_service(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    config_entry_setup: MockConfigEntry,
) -> None:
    """Test service works and also don't remove more than expected."""
    device = device_registry.async_get_or_create(
        config_entry_id=config_entry_setup.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "123")},
    )

    assert (
        len(
            [
                entry
                for entry in device_registry.devices.values()
                if config_entry_setup.entry_id in entry.config_entries
            ]
        )
        == 5  # Host, gateway, light, switch and orphan
    )

    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "12345",
        suggested_object_id="Orphaned sensor",
        config_entry=config_entry_setup,
        device_id=device.id,
    )

    assert (
        len(
            er.async_entries_for_config_entry(
                entity_registry, config_entry_setup.entry_id
            )
        )
        == 3  # Light, switch battery and orphan
    )

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_REMOVE_ORPHANED_ENTRIES,
        service_data={CONF_BRIDGE_ID: BRIDGE_ID},
    )
    await menuai.async_block_till_done()

    assert (
        len(
            [
                entry
                for entry in device_registry.devices.values()
                if config_entry_setup.entry_id in entry.config_entries
            ]
        )
        == 4  # Host, gateway, light and switch
    )

    assert (
        len(
            er.async_entries_for_config_entry(
                entity_registry, config_entry_setup.entry_id
            )
        )
        == 2  # Light and switch battery
    )
