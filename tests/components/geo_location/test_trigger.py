"""The tests for the geolocation trigger."""

import logging

import pytest

from menuai.components import automation, zone
from menuai.const import (
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    STATE_UNAVAILABLE,
)
from menuai.core import Context, menuai, ServiceCall
from menuai.setup import async_setup_component

from tests.common import async_mock_service, mock_component


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.fixture
def calls(menuai: menuai) -> list[ServiceCall]:
    """Track calls to a mock service."""
    return async_mock_service(menuai, "test", "automation")


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
        "geo_location.entity",
        "hello",
        {"latitude": 32.881011, "longitude": -117.234758, "source": "test_source"},
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "geo_location",
                    "source": "test_source",
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
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564},
        context=context,
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 1
    assert service_calls[0].context.parent_id == context.id
    assert (
        service_calls[0].data["some"]
        == "geo_location - geo_location.entity - hello - hello - test - 0"
    )

    # Set out of zone again so we can trigger call
    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.881011, "longitude": -117.234758},
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
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564},
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 2


async def test_if_not_fires_for_enter_on_zone_leave(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing on zone leave."""
    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564, "source": "test_source"},
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "geo_location",
                    "source": "test_source",
                    "zone": "zone.test",
                    "event": "enter",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.881011, "longitude": -117.234758},
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 0


async def test_if_fires_on_zone_leave(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on zone leave."""
    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564, "source": "test_source"},
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "geo_location",
                    "source": "test_source",
                    "zone": "zone.test",
                    "event": "leave",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.881011, "longitude": -117.234758, "source": "test_source"},
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 1


async def test_if_fires_on_zone_leave_2(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing on zone leave for unavailable entity."""
    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564, "source": "test_source"},
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "geo_location",
                    "source": "test_source",
                    "zone": "zone.test",
                    "event": "enter",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set(
        "geo_location.entity",
        STATE_UNAVAILABLE,
        {"source": "test_source"},
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 0


async def test_if_not_fires_for_leave_on_zone_enter(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for not firing on zone enter."""
    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.881011, "longitude": -117.234758, "source": "test_source"},
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "geo_location",
                    "source": "test_source",
                    "zone": "zone.test",
                    "event": "leave",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564},
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 0


async def test_if_fires_on_zone_appear(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if entity appears in zone."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "geo_location",
                    "source": "test_source",
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
                        )
                    },
                },
            }
        },
    )

    # Entity appears in zone without previously existing outside the zone.
    context = Context()
    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564, "source": "test_source"},
        context=context,
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 1
    assert service_calls[0].context.parent_id == context.id
    assert (
        service_calls[0].data["some"]
        == "geo_location - geo_location.entity -  - hello - test"
    )


async def test_if_fires_on_zone_appear_2(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if entity appears in zone."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "geo_location",
                    "source": "test_source",
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
                        )
                    },
                },
            }
        },
    )

    # Entity appears in zone without previously existing outside the zone.
    context = Context()
    menuai.states.async_set(
        "geo_location.entity",
        "goodbye",
        {"latitude": 32.881011, "longitude": -117.234758, "source": "test_source"},
        context=context,
    )
    await menuai.async_block_till_done()

    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564, "source": "test_source"},
        context=context,
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 1
    assert service_calls[0].context.parent_id == context.id
    assert (
        service_calls[0].data["some"]
        == "geo_location - geo_location.entity - goodbye - hello - test"
    )


async def test_if_fires_on_zone_disappear(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for firing if entity disappears from zone."""
    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564, "source": "test_source"},
    )
    await menuai.async_block_till_done()

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "geo_location",
                    "source": "test_source",
                    "zone": "zone.test",
                    "event": "leave",
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
                        )
                    },
                },
            }
        },
    )

    # Entity disappears from zone without new coordinates outside the zone.
    menuai.states.async_remove("geo_location.entity")
    await menuai.async_block_till_done()

    assert len(service_calls) == 1
    assert (
        service_calls[0].data["some"]
        == "geo_location - geo_location.entity - hello -  - test"
    )


async def test_zone_undefined(
    menuai: menuai,
    service_calls: list[ServiceCall],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for undefined zone."""
    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.880586, "longitude": -117.237564, "source": "test_source"},
    )
    await menuai.async_block_till_done()

    caplog.set_level(logging.WARNING)

    zone_does_not_exist = "zone.does_not_exist"
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "geo_location",
                    "source": "test_source",
                    "zone": zone_does_not_exist,
                    "event": "leave",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    menuai.states.async_set(
        "geo_location.entity",
        "hello",
        {"latitude": 32.881011, "longitude": -117.234758, "source": "test_source"},
    )
    await menuai.async_block_till_done()

    assert len(service_calls) == 0

    assert (
        f"Unable to execute automation automation 0: Zone {zone_does_not_exist} not found"
        in caplog.text
    )
