"""The tests device sun light trigger component."""

from collections.abc import Callable
from datetime import datetime
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components import (
    device_sun_light_trigger,
    device_tracker,
    group,
    light,
)
from menuai.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    CONF_PLATFORM,
    EVENT_menuai_START,
    STATE_HOME,
    STATE_NOT_HOME,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
)
from menuai.core import CoreState, menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed, setup_test_component_platform
from tests.components.device_tracker.common import MockScanner
from tests.components.light.common import MockLight


@pytest.fixture
async def scanner(
    menuai: menuai,
    mock_light_entities: list[MockLight],
    mock_legacy_device_scanner: MockScanner,
    mock_legacy_device_tracker_setup: Callable[[menuai, MockScanner], None],
) -> None:
    """Initialize components."""
    mock_legacy_device_tracker_setup(menuai, mock_legacy_device_scanner)
    mock_legacy_device_scanner.reset()
    mock_legacy_device_scanner.come_home("DEV1")

    setup_test_component_platform(menuai, "light", mock_light_entities)

    with patch(
        "menuai.components.device_tracker.legacy.load_yaml_config_file",
        return_value={
            "device_1": {
                "mac": "DEV1",
                "name": "Unnamed Device",
                "picture": "http://example.com/dev1.jpg",
                "track": True,
                "vendor": None,
            },
            "device_2": {
                "mac": "DEV2",
                "name": "Unnamed Device",
                "picture": "http://example.com/dev2.jpg",
                "track": True,
                "vendor": None,
            },
        },
    ):
        assert await async_setup_component(
            menuai,
            device_tracker.DOMAIN,
            {device_tracker.DOMAIN: {CONF_PLATFORM: "test"}},
        )

    assert await async_setup_component(
        menuai, light.DOMAIN, {light.DOMAIN: {CONF_PLATFORM: "test"}}
    )
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("scanner")
async def test_lights_on_when_sun_sets(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test lights go on when there is someone home and the sun sets."""
    test_time = datetime(2017, 4, 5, 1, 2, 3, tzinfo=dt_util.UTC)
    freezer.move_to(test_time)
    assert await async_setup_component(
        menuai, device_sun_light_trigger.DOMAIN, {device_sun_light_trigger.DOMAIN: {}}
    )

    await menuai.services.async_call(
        light.DOMAIN,
        light.SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "test.light"},
        blocking=True,
    )

    test_time = test_time.replace(hour=3)
    freezer.move_to(test_time)
    async_fire_time_changed(menuai, test_time)
    await menuai.async_block_till_done()

    assert all(
        menuai.states.get(ent_id).state == STATE_ON
        for ent_id in menuai.states.async_entity_ids("light")
    )


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_lights_turn_off_when_everyone_leaves(menuai: menuai) -> None:
    """Test lights turn off when everyone leaves the house."""
    assert await async_setup_component(
        menuai, "light", {light.DOMAIN: {CONF_PLATFORM: "test"}}
    )
    await menuai.services.async_call(
        light.DOMAIN,
        light.SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "test.light"},
        blocking=True,
    )
    menuai.states.async_set("device_tracker.bla", STATE_HOME)

    assert await async_setup_component(
        menuai, device_sun_light_trigger.DOMAIN, {device_sun_light_trigger.DOMAIN: {}}
    )

    menuai.states.async_set("device_tracker.bla", STATE_NOT_HOME)

    await menuai.async_block_till_done()

    assert all(
        menuai.states.get(ent_id).state == STATE_OFF
        for ent_id in menuai.states.async_entity_ids("light")
    )


@pytest.mark.usefixtures("scanner")
async def test_lights_turn_on_when_coming_home_after_sun_set(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test lights turn on when coming home after sun set."""
    test_time = datetime(2017, 4, 5, 3, 2, 3, tzinfo=dt_util.UTC)
    freezer.move_to(test_time)
    await menuai.services.async_call(
        light.DOMAIN, light.SERVICE_TURN_OFF, {ATTR_ENTITY_ID: "all"}, blocking=True
    )

    assert await async_setup_component(
        menuai, device_sun_light_trigger.DOMAIN, {device_sun_light_trigger.DOMAIN: {}}
    )

    menuai.states.async_set(f"{DEVICE_TRACKER_DOMAIN}.device_2", STATE_UNKNOWN)
    await menuai.async_block_till_done()
    assert all(
        menuai.states.get(ent_id).state == STATE_OFF
        for ent_id in menuai.states.async_entity_ids("light")
    )

    menuai.states.async_set(f"{DEVICE_TRACKER_DOMAIN}.device_2", STATE_NOT_HOME)
    await menuai.async_block_till_done()
    assert all(
        menuai.states.get(ent_id).state == STATE_OFF
        for ent_id in menuai.states.async_entity_ids("light")
    )

    menuai.states.async_set(f"{DEVICE_TRACKER_DOMAIN}.device_2", STATE_HOME)
    await menuai.async_block_till_done()
    assert all(
        menuai.states.get(ent_id).state == light.STATE_ON
        for ent_id in menuai.states.async_entity_ids("light")
    )


@pytest.mark.usefixtures("scanner")
async def test_lights_turn_on_when_coming_home_after_sun_set_person(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test lights turn on when coming home after sun set."""
    # Ensure all setup tasks are done (avoid flaky tests)
    await menuai.async_block_till_done(wait_background_tasks=True)

    device_1 = f"{DEVICE_TRACKER_DOMAIN}.device_1"
    device_2 = f"{DEVICE_TRACKER_DOMAIN}.device_2"

    test_time = datetime(2017, 4, 5, 3, 2, 3, tzinfo=dt_util.UTC)
    freezer.move_to(test_time)
    await menuai.services.async_call(
        light.DOMAIN, light.SERVICE_TURN_OFF, {ATTR_ENTITY_ID: "all"}, blocking=True
    )
    menuai.states.async_set(device_1, STATE_NOT_HOME)
    menuai.states.async_set(device_2, STATE_NOT_HOME)
    await menuai.async_block_till_done()

    assert all(
        not light.is_on(menuai, ent_id)
        for ent_id in menuai.states.async_entity_ids("light")
    )
    assert menuai.states.get(device_1).state == "not_home"
    assert menuai.states.get(device_2).state == "not_home"

    assert await async_setup_component(
        menuai,
        "person",
        {"person": [{"id": "me", "name": "Me", "device_trackers": [device_1]}]},
    )

    assert await async_setup_component(menuai, "group", {})
    await menuai.async_block_till_done()
    await group.Group.async_create_group(
        menuai,
        "person_me",
        created_by_service=False,
        entity_ids=["person.me"],
        icon=None,
        mode=None,
        object_id=None,
        order=None,
    )

    assert await async_setup_component(
        menuai,
        device_sun_light_trigger.DOMAIN,
        {device_sun_light_trigger.DOMAIN: {"device_group": "group.person_me"}},
    )

    assert all(
        menuai.states.get(ent_id).state == STATE_OFF
        for ent_id in menuai.states.async_entity_ids("light")
    )
    assert menuai.states.get(device_1).state == "not_home"
    assert menuai.states.get(device_2).state == "not_home"
    assert menuai.states.get("person.me").state == "not_home"

    # Unrelated device has no impact
    menuai.states.async_set(device_2, STATE_HOME)
    await menuai.async_block_till_done()

    assert all(
        menuai.states.get(ent_id).state == STATE_OFF
        for ent_id in menuai.states.async_entity_ids("light")
    )
    assert menuai.states.get(device_1).state == "not_home"
    assert menuai.states.get(device_2).state == "home"
    assert menuai.states.get("person.me").state == "not_home"

    # person home switches on
    menuai.states.async_set(device_1, STATE_HOME)
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert all(
        menuai.states.get(ent_id).state == light.STATE_ON
        for ent_id in menuai.states.async_entity_ids("light")
    )
    assert menuai.states.get(device_1).state == "home"
    assert menuai.states.get(device_2).state == "home"
    assert menuai.states.get("person.me").state == "home"


async def test_initialize_start(menuai: menuai) -> None:
    """Test we initialize when HA starts."""
    menuai.set_state(CoreState.not_running)
    assert await async_setup_component(
        menuai,
        device_sun_light_trigger.DOMAIN,
        {device_sun_light_trigger.DOMAIN: {}},
    )

    with patch(
        "menuai.components.device_sun_light_trigger.activate_automation"
    ) as mock_activate:
        menuai.bus.fire(EVENT_menuai_START)
        await menuai.async_block_till_done()
        await menuai.async_block_till_done()

    assert len(mock_activate.mock_calls) == 1
