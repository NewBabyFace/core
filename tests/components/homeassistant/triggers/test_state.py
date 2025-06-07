"""The test for state automation."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components import automation
from menuai.components.menuai.triggers import state as state_trigger
from menuai.const import (
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    STATE_UNAVAILABLE,
)
from menuai.core import Context, menuai, ServiceCall
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import assert_setup_component, async_fire_time_changed, mock_component


@pytest.fixture(autouse=True)
def setup_comp(menuai: menuai) -> None:
    """Initialize components."""
    mock_component(menuai, "group")
    menuai.states.async_set("test.entity", "hello")


async def test_if_fires_on_entity_change(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity change."""
    context = Context()
    menuai.states.async_set("test.entity", "hello")
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "state", "entity_id": "test.entity"},
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": (
                            "{{ trigger.platform }}"
                            " - {{ trigger.entity_id }}"
                            " - {{ trigger.from_state.state }}"
                            " - {{ trigger.to_state.state }}"
                            " - {{ trigger.for }}"
                            " - {{ trigger.id }}"
                        )
                    },
                },
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world", context=context)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].context.parent_id == context.id
    assert (
        service_calls[0].data["some"]
        == "state - test.entity - hello - world - None - 0"
    )

    await menuai.services.async_call(
        automation.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_MATCH_ALL},
        blocking=True,
    )
    assert len(service_calls) == 2
    menuai.states.async_set("test.entity", "planet")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2


async def test_if_fires_on_entity_change_uuid(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
) -> None:
    """Test for firing on entity change."""
    context = Context()

    entry = entity_registry.async_get_or_create(
        "test", "hue", "1234", suggested_object_id="beer"
    )

    assert entry.entity_id == "test.beer"

    menuai.states.async_set("test.beer", "hello")
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "state", "entity_id": entry.id},
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": (
                            "{{ trigger.platform }}"
                            " - {{ trigger.entity_id }}"
                            " - {{ trigger.from_state.state }}"
                            " - {{ trigger.to_state.state }}"
                            " - {{ trigger.for }}"
                            " - {{ trigger.id }}"
                        )
                    },
                },
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.beer", "world", context=context)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].context.parent_id == context.id
    assert (
        service_calls[0].data["some"] == "state - test.beer - hello - world - None - 0"
    )

    await menuai.services.async_call(
        automation.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_MATCH_ALL},
        blocking=True,
    )
    assert len(service_calls) == 2
    menuai.states.async_set("test.beer", "planet")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2


async def test_if_fires_on_entity_change_with_from_filter(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity change with filter."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "from": "hello",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_not_from_filter(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity change inverse filter."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "not_from": "hello",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    # Do not fire from hello
    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert not service_calls

    menuai.states.async_set("test.entity", "universum")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_to_filter(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity change with to filter."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_not_to_filter(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity change with to filter."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "not_to": "world",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    # Do not fire to world
    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert not service_calls

    menuai.states.async_set("test.entity", "universum")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_from_filter_all(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity change with filter."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "from": None,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    menuai.states.async_set("test.entity", "world", {"attribute": 5})
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_to_filter_all(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity change with to filter."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": None,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    menuai.states.async_set("test.entity", "world", {"attribute": 5})
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_attribute_change_with_to_filter(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing on attribute change."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world", {"test_attribute": 11})
    menuai.states.async_set("test.entity", "world", {"test_attribute": 12})
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_both_filters(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if both filters are a non match."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "from": "hello",
                    "to": "world",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_not_from_to(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if not from doesn't match and to match."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "not_from": ["hello", "galaxy"],
                    "to": ["galaxy", "universe"],
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    # We should not trigger from hello
    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert not service_calls

    # We should not trigger to != galaxy
    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert not service_calls

    # We should trigger to galaxy
    menuai.states.async_set("test.entity", "galaxy")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # We should not trigger from milky way
    menuai.states.async_set("test.entity", "milky_way")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # We should trigger to universe
    menuai.states.async_set("test.entity", "universe")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2


async def test_if_fires_on_entity_change_with_from_not_to(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if not from doesn't match and to match."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "from": ["hello", "galaxy"],
                    "not_to": ["galaxy", "universe"],
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    # We should trigger to world from hello
    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # Reset back to hello, should not trigger
    menuai.states.async_set("test.entity", "hello")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # We should not trigger to galaxy
    menuai.states.async_set("test.entity", "galaxy")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # We should trigger form galaxy to milky way
    menuai.states.async_set("test.entity", "milky_way")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2

    # We should not trigger to universe
    menuai.states.async_set("test.entity", "universe")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2


async def test_if_not_fires_if_to_filter_not_match(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing if to filter is not a match."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "from": "hello",
                    "to": "world",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "moon")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0


async def test_if_not_fires_if_from_filter_not_match(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing if from filter is not a match."""
    menuai.states.async_set("test.entity", "bye")

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "from": "hello",
                    "to": "world",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0


async def test_if_not_fires_if_entity_not_match(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing if entity is not matching."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "state", "entity_id": "test.another_entity"},
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0


async def test_if_action(menuai: menuai, service_calls: list[ServiceCall]) -> None:
    """Test for to action."""
    entity_id = "domain.test_entity"
    test_state = "new_state"
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "condition": [
                    {"condition": "state", "entity_id": entity_id, "state": test_state}
                ],
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set(entity_id, test_state)
    menuai.bus.async_fire("test_event")
    await menuai.async_block_till_done()

    assert len(service_calls) == 1

    menuai.states.async_set(entity_id, test_state + "something")
    menuai.bus.async_fire("test_event")
    await menuai.async_block_till_done()

    assert len(service_calls) == 1


async def test_if_fails_setup_if_to_boolean_value(menuai: menuai) -> None:
    """Test for setup failure for boolean to."""
    with assert_setup_component(1, automation.DOMAIN):
        assert await async_setup_component(
            menuai,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {
                        "platform": "state",
                        "entity_id": "test.entity",
                        "to": True,
                    },
                    "action": {"service": "menuai.turn_on"},
                }
            },
        )
    assert menuai.states.get("automation.automation_0").state == STATE_UNAVAILABLE


async def test_if_fails_setup_if_from_boolean_value(menuai: menuai) -> None:
    """Test for setup failure for boolean from."""
    with assert_setup_component(1, automation.DOMAIN):
        assert await async_setup_component(
            menuai,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {
                        "platform": "state",
                        "entity_id": "test.entity",
                        "from": True,
                    },
                    "action": {"service": "menuai.turn_on"},
                }
            },
        )
    assert menuai.states.get("automation.automation_0").state == STATE_UNAVAILABLE


async def test_if_fails_setup_bad_for(menuai: menuai) -> None:
    """Test for setup failure for bad for."""
    with assert_setup_component(1, automation.DOMAIN):
        assert await async_setup_component(
            menuai,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {
                        "platform": "state",
                        "entity_id": "test.entity",
                        "to": "world",
                        "for": {"invalid": 5},
                    },
                    "action": {"service": "menuai.turn_on"},
                }
            },
        )
    assert menuai.states.get("automation.automation_0").state == STATE_UNAVAILABLE


async def test_if_not_fires_on_entity_change_with_for(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing on entity change with for."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    menuai.states.async_set("test.entity", "not_world")
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 0


async def test_if_not_fires_on_entities_change_with_for_after_stop(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing on entity change with for after stop trigger."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "to": "world",
                    "for": {"seconds": 5},
                },
                "action": [
                    {"delay": "0.0001"},
                    {"service": "test.automation"},
                ],
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity_1", "world")
    menuai.states.async_set("test.entity_2", "world")
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    menuai.states.async_set("test.entity_1", "world_no")
    menuai.states.async_set("test.entity_2", "world_no")
    await menuai.async_block_till_done()
    menuai.states.async_set("test.entity_1", "world")
    menuai.states.async_set("test.entity_2", "world")
    await menuai.async_block_till_done()
    await menuai.services.async_call(
        automation.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_MATCH_ALL},
        blocking=True,
    )
    assert len(service_calls) == 2

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 2


async def test_if_fires_on_entity_change_with_for_attribute_change(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_calls: list[ServiceCall],
) -> None:
    """Test for firing on entity change with for and attribute change."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=4))
    async_fire_time_changed(menuai)
    menuai.states.async_set(
        "test.entity", "world", attributes={"mock_attr": "attr_change"}
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    freezer.tick(timedelta(seconds=4))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_for_multiple_force_update(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_calls: list[ServiceCall],
) -> None:
    """Test for firing on entity change with for and force update."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.force_entity",
                    "to": "world",
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.force_entity", "world", None, True)
    await menuai.async_block_till_done()
    for _ in range(4):
        freezer.tick(timedelta(seconds=1))
        async_fire_time_changed(menuai)
        menuai.states.async_set("test.force_entity", "world", None, True)
        await menuai.async_block_till_done()
    assert len(service_calls) == 0
    freezer.tick(timedelta(seconds=4))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_for(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity change with for."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_entity_change_with_for_without_to(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity change with for."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "hello")
    await menuai.async_block_till_done()

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=2))
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=4))
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_does_not_fires_on_entity_change_with_for_without_to_2(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_calls: list[ServiceCall],
) -> None:
    """Test for firing on entity change with for."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    for i in range(10):
        menuai.states.async_set("test.entity", str(i))
        await menuai.async_block_till_done()
        freezer.tick(timedelta(seconds=1))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    assert len(service_calls) == 0


async def test_if_fires_on_entity_creation_and_removal(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on entity creation and removal, with to/from constraints."""
    # set automations for multiple combinations to/from
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {"platform": "state", "entity_id": "test.entity_0"},
                    "action": {"service": "test.automation"},
                },
                {
                    "trigger": {
                        "platform": "state",
                        "from": "hello",
                        "entity_id": "test.entity_1",
                    },
                    "action": {"service": "test.automation"},
                },
                {
                    "trigger": {
                        "platform": "state",
                        "to": "world",
                        "entity_id": "test.entity_2",
                    },
                    "action": {"service": "test.automation"},
                },
            ],
        },
    )
    await menuai.async_block_till_done()

    # use contexts to identify trigger entities
    context_0 = Context()
    context_1 = Context()
    context_2 = Context()

    # automation with match_all triggers on creation
    menuai.states.async_set("test.entity_0", "any", context=context_0)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].context.parent_id == context_0.id

    # create entities, trigger on test.entity_2 ('to' matches, no 'from')
    menuai.states.async_set("test.entity_1", "hello", context=context_1)
    menuai.states.async_set("test.entity_2", "world", context=context_2)
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert service_calls[1].context.parent_id == context_2.id

    # removal of both, trigger on test.entity_1 ('from' matches, no 'to')
    assert menuai.states.async_remove("test.entity_1", context=context_1)
    assert menuai.states.async_remove("test.entity_2", context=context_2)
    await menuai.async_block_till_done()
    assert len(service_calls) == 3
    assert service_calls[2].context.parent_id == context_1.id

    # automation with match_all triggers on removal
    assert menuai.states.async_remove("test.entity_0", context=context_0)
    await menuai.async_block_till_done()
    assert len(service_calls) == 4
    assert service_calls[3].context.parent_id == context_0.id


async def test_if_fires_on_for_condition(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if condition is on."""
    point1 = dt_util.utcnow()
    point2 = point1 + timedelta(seconds=10)
    with patch("menuai.core.dt_util.utcnow") as mock_utcnow:
        mock_utcnow.return_value = point1
        menuai.states.async_set("test.entity", "on")
        assert await async_setup_component(
            menuai,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "condition": {
                        "condition": "state",
                        "entity_id": "test.entity",
                        "state": "on",
                        "for": {"seconds": 5},
                    },
                    "action": {"service": "test.automation"},
                }
            },
        )
        await menuai.async_block_till_done()

        # not enough time has passed
        menuai.bus.async_fire("test_event")
        await menuai.async_block_till_done()
        assert len(service_calls) == 0

        # Time travel 10 secs into the future
        mock_utcnow.return_value = point2
        menuai.bus.async_fire("test_event")
        await menuai.async_block_till_done()
        assert len(service_calls) == 1


async def test_if_fires_on_for_condition_attribute_change(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if condition is on with attribute change."""
    point1 = dt_util.utcnow()
    point2 = point1 + timedelta(seconds=4)
    point3 = point1 + timedelta(seconds=8)
    with patch("menuai.core.dt_util.utcnow") as mock_utcnow:
        mock_utcnow.return_value = point1
        menuai.states.async_set("test.entity", "on")
        assert await async_setup_component(
            menuai,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "condition": {
                        "condition": "state",
                        "entity_id": "test.entity",
                        "state": "on",
                        "for": {"seconds": 5},
                    },
                    "action": {"service": "test.automation"},
                }
            },
        )
        await menuai.async_block_till_done()

        # not enough time has passed
        menuai.bus.async_fire("test_event")
        await menuai.async_block_till_done()
        assert len(service_calls) == 0

        # Still not enough time has passed, but an attribute is changed
        mock_utcnow.return_value = point2
        menuai.states.async_set(
            "test.entity", "on", attributes={"mock_attr": "attr_change"}
        )
        menuai.bus.async_fire("test_event")
        await menuai.async_block_till_done()
        assert len(service_calls) == 0

        # Enough time has now passed
        mock_utcnow.return_value = point3
        menuai.bus.async_fire("test_event")
        await menuai.async_block_till_done()
        assert len(service_calls) == 1


async def test_if_fails_setup_for_without_time(menuai: menuai) -> None:
    """Test for setup failure if no time is provided."""
    with assert_setup_component(1, automation.DOMAIN):
        assert await async_setup_component(
            menuai,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {"platform": "event", "event_type": "bla"},
                    "condition": {
                        "condition": "state",
                        "entity_id": "test.entity",
                        "state": "on",
                        "for": {},
                    },
                    "action": {"service": "test.automation"},
                }
            },
        )
    assert menuai.states.get("automation.automation_0").state == STATE_UNAVAILABLE


async def test_if_fails_setup_for_without_entity(menuai: menuai) -> None:
    """Test for setup failure if no entity is provided."""
    with assert_setup_component(1, automation.DOMAIN):
        assert await async_setup_component(
            menuai,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {"platform": "event", "event_type": "bla"},
                    "condition": {
                        "condition": "state",
                        "state": "on",
                        "for": {"seconds": 5},
                    },
                    "action": {"service": "test.automation"},
                }
            },
        )
    assert menuai.states.get("automation.automation_0").state == STATE_UNAVAILABLE


async def test_wait_template_with_trigger(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test using wait template with 'trigger.entity_id'."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                },
                "action": [
                    {"wait_template": "{{ is_state(trigger.entity_id, 'hello') }}"},
                    {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "{{ trigger.platform }}"
                                " - {{ trigger.entity_id }}"
                                " - {{ trigger.from_state.state }}"
                                " - {{ trigger.to_state.state }}"
                            )
                        },
                    },
                ],
            }
        },
    )

    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "world")
    menuai.states.async_set("test.entity", "hello")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["some"] == "state - test.entity - hello - world"


async def test_if_fires_on_entities_change_no_overlap(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_calls: list[ServiceCall],
) -> None:
    """Test for firing on entities change with no overlap."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "to": "world",
                    "for": {"seconds": 5},
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {"some": "{{ trigger.entity_id }}"},
                },
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity_1", "world")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["some"] == "test.entity_1"

    menuai.states.async_set("test.entity_2", "world")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert service_calls[1].data["some"] == "test.entity_2"


async def test_if_fires_on_entities_change_overlap(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_calls: list[ServiceCall],
) -> None:
    """Test for firing on entities change with overlap."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "to": "world",
                    "for": {"seconds": 5},
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {"some": "{{ trigger.entity_id }}"},
                },
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity_1", "world")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    menuai.states.async_set("test.entity_2", "world")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    menuai.states.async_set("test.entity_2", "hello")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    menuai.states.async_set("test.entity_2", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    freezer.tick(timedelta(seconds=3))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["some"] == "test.entity_1"

    freezer.tick(timedelta(seconds=3))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert service_calls[1].data["some"] == "test.entity_2"


async def test_if_fires_on_change_with_for_template_1(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on change with for template."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                    "for": {"seconds": "{{ 5 }}"},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_change_with_for_template_2(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on change with for template."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                    "for": "{{ 5 }}",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_change_with_for_template_3(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on change with for template."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                    "for": "00:00:{{ 5 }}",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_change_with_for_template_4(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on change with for template."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger_variables": {"seconds": 5},
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                    "for": {"seconds": "{{ seconds }}"},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set("test.entity", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_change_from_with_for(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on change with from/for."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "media_player.foo",
                    "from": "playing",
                    "for": "00:00:30",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set("media_player.foo", "playing")
    await menuai.async_block_till_done()
    menuai.states.async_set("media_player.foo", "paused")
    await menuai.async_block_till_done()
    menuai.states.async_set("media_player.foo", "stopped")
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=1))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_not_fires_on_change_from_with_for(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on change with from/for."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "media_player.foo",
                    "from": "playing",
                    "for": "00:00:30",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set("media_player.foo", "playing")
    await menuai.async_block_till_done()
    menuai.states.async_set("media_player.foo", "paused")
    await menuai.async_block_till_done()
    menuai.states.async_set("media_player.foo", "playing")
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=1))
    await menuai.async_block_till_done()
    assert len(service_calls) == 0


async def test_invalid_for_template_1(menuai: menuai) -> None:
    """Test for invalid for template."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "to": "world",
                    "for": {"seconds": "{{ five }}"},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    with patch.object(state_trigger, "_LOGGER") as mock_logger:
        menuai.states.async_set("test.entity", "world")
        await menuai.async_block_till_done()
        assert mock_logger.error.called


async def test_if_fires_on_entities_change_overlap_for_template(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_calls: list[ServiceCall],
) -> None:
    """Test for firing on entities change with overlap and for template."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "to": "world",
                    "for": '{{ 5 if trigger.entity_id == "test.entity_1" else 10 }}',
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": "{{ trigger.entity_id }} - {{ trigger.for }}"
                    },
                },
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity_1", "world")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    menuai.states.async_set("test.entity_2", "world")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    menuai.states.async_set("test.entity_2", "hello")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    menuai.states.async_set("test.entity_2", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    freezer.tick(timedelta(seconds=3))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["some"] == "test.entity_1 - 0:00:05"

    freezer.tick(timedelta(seconds=3))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    freezer.tick(timedelta(seconds=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert service_calls[1].data["some"] == "test.entity_2 - 0:00:10"


async def test_attribute_if_fires_on_entity_change_with_both_filters(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if both filters are match attribute."""
    menuai.states.async_set("test.entity", "bla", {"name": "hello"})

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "from": "hello",
                    "to": "world",
                    "attribute": "name",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "bla", {"name": "world"})
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_attribute_if_fires_on_entity_where_attr_stays_constant(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if attribute stays the same."""
    menuai.states.async_set("test.entity", "bla", {"name": "hello", "other": "old_value"})

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "attribute": "name",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    # Leave all attributes the same
    menuai.states.async_set("test.entity", "bla", {"name": "hello", "other": "old_value"})
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    # Change the untracked attribute
    menuai.states.async_set("test.entity", "bla", {"name": "hello", "other": "new_value"})
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    # Change the tracked attribute
    menuai.states.async_set("test.entity", "bla", {"name": "world", "other": "old_value"})
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_attribute_if_fires_on_entity_where_attr_stays_constant_filter(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if attribute stays the same."""
    menuai.states.async_set("test.entity", "bla", {"name": "other_name"})

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "attribute": "name",
                    "to": "best_name",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    # Leave all attributes the same
    menuai.states.async_set(
        "test.entity", "bla", {"name": "best_name", "other": "old_value"}
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # Change the untracked attribute
    menuai.states.async_set(
        "test.entity", "bla", {"name": "best_name", "other": "new_value"}
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # Change the tracked attribute
    menuai.states.async_set(
        "test.entity", "bla", {"name": "other_name", "other": "old_value"}
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_attribute_if_fires_on_entity_where_attr_stays_constant_all(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if attribute stays the same."""
    menuai.states.async_set("test.entity", "bla", {"name": "hello", "other": "old_value"})

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "attribute": "name",
                    "to": None,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    # Leave all attributes the same
    menuai.states.async_set(
        "test.entity", "bla", {"name": "name_1", "other": "old_value"}
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # Change the untracked attribute
    menuai.states.async_set(
        "test.entity", "bla", {"name": "name_1", "other": "new_value"}
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # Change the tracked attribute
    menuai.states.async_set(
        "test.entity", "bla", {"name": "name_2", "other": "old_value"}
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 2


async def test_attribute_if_not_fires_on_entities_change_with_for_after_stop(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing on entity change with for after stop trigger."""
    menuai.states.async_set("test.entity", "bla", {"name": "hello"})

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "from": "hello",
                    "to": "world",
                    "attribute": "name",
                    "for": 5,
                },
                "action": [
                    {"delay": "0.0001"},
                    {"service": "test.automation"},
                ],
            }
        },
    )
    await menuai.async_block_till_done()

    # Test that the for-check works
    menuai.states.async_set("test.entity", "bla", {"name": "world"})
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=2))
    menuai.states.async_set("test.entity", "bla", {"name": "world", "something": "else"})
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    # Now remove state while inside "for"
    menuai.states.async_set("test.entity", "bla", {"name": "hello"})
    menuai.states.async_set("test.entity", "bla", {"name": "world"})
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    menuai.states.async_remove("test.entity")
    await menuai.async_block_till_done()

    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_attribute_if_fires_on_entity_change_with_both_filters_boolean(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if both filters are match attribute."""
    menuai.states.async_set("test.entity", "bla", {"happening": False})

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "state",
                    "entity_id": "test.entity",
                    "from": False,
                    "to": True,
                    "attribute": "happening",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity", "bla", {"happening": True})
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_variables_priority(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    service_calls: list[ServiceCall],
) -> None:
    """Test an externally defined trigger variable is overridden."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger_variables": {"trigger": "illegal"},
                "trigger": {
                    "platform": "state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "to": "world",
                    "for": '{{ 5 if trigger.entity_id == "test.entity_1" else 10 }}',
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": "{{ trigger.entity_id }} - {{ trigger.for }}"
                    },
                },
            }
        },
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("test.entity_1", "world")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    menuai.states.async_set("test.entity_2", "world")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    menuai.states.async_set("test.entity_2", "hello")
    await menuai.async_block_till_done()
    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(menuai)
    menuai.states.async_set("test.entity_2", "world")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0
    freezer.tick(timedelta(seconds=3))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["some"] == "test.entity_1 - 0:00:05"

    freezer.tick(timedelta(seconds=3))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    freezer.tick(timedelta(seconds=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert service_calls[1].data["some"] == "test.entity_2 - 0:00:10"
