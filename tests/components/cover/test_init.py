"""The tests for Cover."""

from enum import Enum

import pytest

from menuai.components import cover
from menuai.components.cover import CoverState
from menuai.const import ATTR_ENTITY_ID, CONF_PLATFORM, SERVICE_TOGGLE
from menuai.core import menuai, ServiceResponse
from menuai.helpers.entity import Entity
from menuai.setup import async_setup_component

from .common import MockCover

from tests.common import (
    MockEntityPlatform,
    help_test_all,
    setup_test_component_platform,
)


async def test_services(
    menuai: menuai,
    mock_cover_entities: list[MockCover],
) -> None:
    """Test the provided services."""
    setup_test_component_platform(menuai, cover.DOMAIN, mock_cover_entities)

    assert await async_setup_component(
        menuai, cover.DOMAIN, {cover.DOMAIN: {CONF_PLATFORM: "test"}}
    )
    await menuai.async_block_till_done()

    # ent1 = cover without tilt and position
    # ent2 = cover with position but no tilt
    # ent3 = cover with simple tilt functions and no position
    # ent4 = cover with all tilt functions but no position
    # ent5 = cover with all functions
    # ent6 = cover with only open/close, but also reports opening/closing
    ent1, ent2, ent3, ent4, ent5, ent6 = mock_cover_entities

    # Test init all covers should be open
    assert is_open(menuai, ent1)
    assert is_open(menuai, ent2)
    assert is_open(menuai, ent3)
    assert is_open(menuai, ent4)
    assert is_open(menuai, ent5)
    assert is_open(menuai, ent6)

    # call basic toggle services
    await call_service(menuai, SERVICE_TOGGLE, ent1)
    await call_service(menuai, SERVICE_TOGGLE, ent2)
    await call_service(menuai, SERVICE_TOGGLE, ent3)
    await call_service(menuai, SERVICE_TOGGLE, ent4)
    await call_service(menuai, SERVICE_TOGGLE, ent5)
    await call_service(menuai, SERVICE_TOGGLE, ent6)

    # entities should be either closed or closing, depending on if they report transitional states
    assert is_closed(menuai, ent1)
    assert is_closing(menuai, ent2)
    assert is_closed(menuai, ent3)
    assert is_closed(menuai, ent4)
    assert is_closing(menuai, ent5)
    assert is_closing(menuai, ent6)

    # call basic toggle services and set different cover position states
    await call_service(menuai, SERVICE_TOGGLE, ent1)
    set_cover_position(ent2, 0)
    await call_service(menuai, SERVICE_TOGGLE, ent2)
    await call_service(menuai, SERVICE_TOGGLE, ent3)
    await call_service(menuai, SERVICE_TOGGLE, ent4)
    set_cover_position(ent5, 15)
    await call_service(menuai, SERVICE_TOGGLE, ent5)
    await call_service(menuai, SERVICE_TOGGLE, ent6)

    # entities should be in correct state depending on the SUPPORT_STOP feature and cover position
    assert is_open(menuai, ent1)
    assert is_closed(menuai, ent2)
    assert is_open(menuai, ent3)
    assert is_open(menuai, ent4)
    assert is_open(menuai, ent5)
    assert is_opening(menuai, ent6)

    # call basic toggle services
    await call_service(menuai, SERVICE_TOGGLE, ent1)
    await call_service(menuai, SERVICE_TOGGLE, ent2)
    await call_service(menuai, SERVICE_TOGGLE, ent3)
    await call_service(menuai, SERVICE_TOGGLE, ent4)
    await call_service(menuai, SERVICE_TOGGLE, ent5)
    await call_service(menuai, SERVICE_TOGGLE, ent6)

    # entities should be in correct state depending on the SUPPORT_STOP feature and cover position
    assert is_closed(menuai, ent1)
    assert is_opening(menuai, ent2)
    assert is_closed(menuai, ent3)
    assert is_closed(menuai, ent4)
    assert is_opening(menuai, ent5)
    assert is_closing(menuai, ent6)

    # Without STOP but still reports opening/closing has a 4th possible toggle state
    set_state(ent6, CoverState.CLOSED)
    await call_service(menuai, SERVICE_TOGGLE, ent6)
    assert is_opening(menuai, ent6)

    # After the unusual state transition: closing -> fully open, toggle should close
    set_state(ent5, CoverState.OPEN)
    await call_service(menuai, SERVICE_TOGGLE, ent5)  # Start closing
    assert is_closing(menuai, ent5)
    set_state(
        ent5, CoverState.OPEN
    )  # Unusual state transition from closing -> fully open
    set_cover_position(ent5, 100)
    await call_service(menuai, SERVICE_TOGGLE, ent5)  # Should close, not open
    assert is_closing(menuai, ent5)


def call_service(menuai: menuai, service: str, ent: Entity) -> ServiceResponse:
    """Call any service on entity."""
    return menuai.services.async_call(
        cover.DOMAIN, service, {ATTR_ENTITY_ID: ent.entity_id}, blocking=True
    )


def set_cover_position(ent, position) -> None:
    """Set a position value to a cover."""
    ent._values["current_cover_position"] = position


def set_state(ent, state) -> None:
    """Set the state of a cover."""
    ent._values["state"] = state


def is_open(menuai: menuai, ent: Entity) -> bool:
    """Return if the cover is closed based on the statemachine."""
    return menuai.states.is_state(ent.entity_id, CoverState.OPEN)


def is_opening(menuai: menuai, ent: Entity) -> bool:
    """Return if the cover is closed based on the statemachine."""
    return menuai.states.is_state(ent.entity_id, CoverState.OPENING)


def is_closed(menuai: menuai, ent: Entity) -> bool:
    """Return if the cover is closed based on the statemachine."""
    return menuai.states.is_state(ent.entity_id, CoverState.CLOSED)


def is_closing(menuai: menuai, ent: Entity) -> bool:
    """Return if the cover is closed based on the statemachine."""
    return menuai.states.is_state(ent.entity_id, CoverState.CLOSING)


def _create_tuples(enum: type[Enum], constant_prefix: str) -> list[tuple[Enum, str]]:
    return [(enum_field, constant_prefix) for enum_field in enum]


def test_all() -> None:
    """Test module.__all__ is correctly set."""
    help_test_all(cover)


def test_deprecated_supported_features_ints(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test deprecated supported features ints."""

    class MockCoverEntity(cover.CoverEntity):
        _attr_supported_features = 1

    entity = MockCoverEntity()
    entity.menuai = menuai
    entity.platform = MockEntityPlatform(menuai)
    assert entity.supported_features is cover.CoverEntityFeature(1)
    assert "MockCoverEntity" in caplog.text
    assert "is using deprecated supported features values" in caplog.text
    assert "Instead it should use" in caplog.text
    assert "CoverEntityFeature.OPEN" in caplog.text
    caplog.clear()
    assert entity.supported_features is cover.CoverEntityFeature(1)
    assert "is using deprecated supported features values" not in caplog.text
