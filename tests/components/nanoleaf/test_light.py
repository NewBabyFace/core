"""Tests for the Nanoleaf light platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.light import ATTR_EFFECT_LIST, DOMAIN as LIGHT_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_nanoleaf: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.nanoleaf.PLATFORMS", [Platform.LIGHT]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize("service", [SERVICE_TURN_ON, SERVICE_TURN_OFF])
async def test_turning_on_or_off_writes_state(
    menuai: menuai,
    mock_nanoleaf: AsyncMock,
    mock_config_entry: MockConfigEntry,
    service: str,
) -> None:
    """Test turning on or off the light writes the state."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("light.nanoleaf").attributes[ATTR_EFFECT_LIST] == [
        "Rainbow",
        "Sunset",
        "Nemo",
    ]

    mock_nanoleaf.effects_list = ["Rainbow", "Sunset", "Nemo", "Something Else"]

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        service,
        {
            ATTR_ENTITY_ID: "light.nanoleaf",
        },
        blocking=True,
    )
    assert menuai.states.get("light.nanoleaf").attributes[ATTR_EFFECT_LIST] == [
        "Rainbow",
        "Sunset",
        "Nemo",
        "Something Else",
    ]
