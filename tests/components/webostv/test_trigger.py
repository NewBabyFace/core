"""The tests for LG webOS TV automation triggers."""

from unittest.mock import patch

import pytest

from menuai.components import automation
from menuai.components.webostv import DOMAIN
from menuai.const import SERVICE_RELOAD
from menuai.core import menuai, ServiceCall
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from . import setup_webostv
from .const import ENTITY_ID, FAKE_UUID

from tests.common import MockEntity, MockEntityPlatform


async def test_webostv_turn_on_trigger_device_id(
    menuai: menuai,
    service_calls: list[ServiceCall],
    device_registry: dr.DeviceRegistry,
    client,
) -> None:
    """Test for turn_on triggers by device_id firing."""
    await setup_webostv(menuai)

    device = device_registry.async_get_device(identifiers={(DOMAIN, FAKE_UUID)})

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "webostv.turn_on",
                        "device_id": device.id,
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": device.id,
                            "id": "{{ trigger.id }}",
                        },
                    },
                },
            ],
        },
    )

    await menuai.services.async_call(
        "media_player",
        "turn_on",
        {"entity_id": ENTITY_ID},
        blocking=True,
    )

    assert len(service_calls) == 2
    assert service_calls[1].data["some"] == device.id
    assert service_calls[1].data["id"] == 0

    with patch("menuai.config.load_yaml_dict", return_value={}):
        await menuai.services.async_call(automation.DOMAIN, SERVICE_RELOAD, blocking=True)

    service_calls.clear()

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            "media_player",
            "turn_on",
            {"entity_id": ENTITY_ID},
            blocking=True,
        )

    assert len(service_calls) == 1


async def test_webostv_turn_on_trigger_entity_id(
    menuai: menuai, service_calls: list[ServiceCall], client
) -> None:
    """Test for turn_on triggers by entity_id firing."""
    await setup_webostv(menuai)

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "webostv.turn_on",
                        "entity_id": ENTITY_ID,
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": ENTITY_ID,
                            "id": "{{ trigger.id }}",
                        },
                    },
                },
            ],
        },
    )

    await menuai.services.async_call(
        "media_player",
        "turn_on",
        {"entity_id": ENTITY_ID},
        blocking=True,
    )

    assert len(service_calls) == 2
    assert service_calls[1].data["some"] == ENTITY_ID
    assert service_calls[1].data["id"] == 0


async def test_unknown_trigger_platform_type(
    menuai: menuai, caplog: pytest.LogCaptureFixture, client
) -> None:
    """Test unknown trigger platform type."""
    await setup_webostv(menuai)

    await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "webostv.unknown",
                        "entity_id": ENTITY_ID,
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": ENTITY_ID,
                            "id": "{{ trigger.id }}",
                        },
                    },
                },
            ],
        },
    )

    assert "Unknown trigger platform: webostv.unknown" in caplog.text


async def test_trigger_invalid_entity_id(
    menuai: menuai, caplog: pytest.LogCaptureFixture, client
) -> None:
    """Test turn on trigger using invalid entity_id."""
    await setup_webostv(menuai)

    platform = MockEntityPlatform(menuai)

    invalid_entity = f"{DOMAIN}.invalid"
    await platform.async_add_entities([MockEntity(name=invalid_entity)])

    await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "webostv.turn_on",
                        "entity_id": invalid_entity,
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": ENTITY_ID,
                            "id": "{{ trigger.id }}",
                        },
                    },
                },
            ],
        },
    )

    assert f"Entity {invalid_entity} is not a valid {DOMAIN} entity" in caplog.text
