"""The tests for the location automation."""

import pytest

from menuai.components import automation, zone
from menuai.const import ATTR_ENTITY_ID, ENTITY_MATCH_ALL, SERVICE_TURN_OFF
from menuai.core import Context, menuai, ServiceCall
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from tests.common import mock_component


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai) -> None:
    """Initialize components."""
    mock_component(menuai, "group")
    await async_setup_component(
        menuai,
        zone.DOMAIN,
        {
            "zone": {
                "name": "test",
                "latitude": 32.880837,
                "longitude": -117.237561,
                "radius": 250,
            }
        },
    )


async def test_if_fires_on_zone_enter(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on zone enter."""
    context = Context()
    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.881011, "longitude": -117.234758}
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "zone",
                    "entity_id": "test.entity",
                    "zone": "zone.test",
                    "event": "enter",
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": (
                            "{{ trigger.platform }}"
                            " - {{ trigger.entity_id }}"
                            " - {{ trigger.from_state.state }}"
                            " - {{ trigger.to_state.state }}"
                            " - {{ trigger.zone.name }}"
                            " - {{ trigger.id }}"
                        )
                    },
                },
            }
        },
    )

    menuai.states.async_set(
        "test.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564},
        context=context,
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 1
    assert service_calls[0].context.parent_id == context.id
    assert (
        service_calls[0].data["some"] == "zone - test.entity - hello - hello - test - 0"
    )

    # Set out of zone again so we can trigger call
    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.881011, "longitude": -117.234758}
    )
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        automation.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_MATCH_ALL},
        blocking=True,
    )
    assert len(service_calls) == 2

    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.880586, "longitude": -117.237564}
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 2


async def test_if_fires_on_zone_enter_uuid(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
) -> None:
    """Test for firing on zone enter when device is specified by entity registry id."""
    context = Context()

    entry = entity_registry.async_get_or_create(
        "test", "hue", "1234", suggested_object_id="entity"
    )
    assert entry.entity_id == "test.entity"

    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.881011, "longitude": -117.234758}
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "zone",
                    "entity_id": entry.id,
                    "zone": "zone.test",
                    "event": "enter",
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": (
                            "{{ trigger.platform }}"
                            " - {{ trigger.entity_id }}"
                            " - {{ trigger.from_state.state }}"
                            " - {{ trigger.to_state.state }}"
                            " - {{ trigger.zone.name }}"
                            " - {{ trigger.id }}"
                        )
                    },
                },
            }
        },
    )

    menuai.states.async_set(
        "test.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564},
        context=context,
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 1
    assert service_calls[0].context.parent_id == context.id
    assert (
        service_calls[0].data["some"] == "zone - test.entity - hello - hello - test - 0"
    )

    # Set out of zone again so we can trigger call
    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.881011, "longitude": -117.234758}
    )
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        automation.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_MATCH_ALL},
        blocking=True,
    )
    assert len(service_calls) == 2

    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.880586, "longitude": -117.237564}
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 2


async def test_if_not_fires_for_enter_on_zone_leave(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing on zone leave."""
    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.880586, "longitude": -117.237564}
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "zone",
                    "entity_id": "test.entity",
                    "zone": "zone.test",
                    "event": "enter",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.881011, "longitude": -117.234758}
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 0


async def test_if_fires_on_zone_leave(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on zone leave."""
    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.880586, "longitude": -117.237564}
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "zone",
                    "entity_id": "test.entity",
                    "zone": "zone.test",
                    "event": "leave",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.881011, "longitude": -117.234758}
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 1


async def test_if_not_fires_for_leave_on_zone_enter(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing on zone enter."""
    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.881011, "longitude": -117.234758}
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "zone",
                    "entity_id": "test.entity",
                    "zone": "zone.test",
                    "event": "leave",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.880586, "longitude": -117.237564}
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 0


async def test_zone_condition(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for zone condition."""
    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.880586, "longitude": -117.237564}
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "condition": {
                    "condition": "zone",
                    "entity_id": "test.entity",
                    "zone": "zone.test",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.bus.async_fire("test_event")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_unknown_zone(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test for firing on zone enter."""
    context = Context()
    menuai.states.async_set(
        "test.entity", "hello", {"latitude": 32.881011, "longitude": -117.234758}
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "My Automation",
                "trigger": {
                    "platform": "zone",
                    "entity_id": "test.entity",
                    "zone": "zone.no_such_zone",
                    "event": "enter",
                },
                "action": {
                    "service": "test.automation",
                },
            }
        },
    )

    assert (
        "Automation 'My Automation' is referencing non-existing zone"
        " 'zone.no_such_zone' in a zone trigger" not in caplog.text
    )

    menuai.states.async_set(
        "test.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564},
        context=context,
    )
    await menuai.async_block_till_done()

    assert (
        "Automation 'My Automation' is referencing non-existing zone"
        " 'zone.no_such_zone' in a zone trigger" in caplog.text
    )
