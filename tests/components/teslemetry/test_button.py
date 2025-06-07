"""Test the Teslemetry button platform."""

from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import assert_entities, setup_platform
from .const import COMMAND_OK


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_button(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Tests that the button entities are correct."""

    entry = await setup_platform(menuai, [Platform.BUTTON])
    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)


@pytest.mark.parametrize(
    ("name", "func"),
    [
        ("wake", "wake_up"),
        ("flash_lights", "flash_lights"),
        ("honk_horn", "honk_horn"),
        ("keyless_driving", "remote_start_drive"),
        ("play_fart", "remote_boombox"),
        ("homelink", "trigger_homelink"),
    ],
)
async def test_press(menuai: menuai, name: str, func: str) -> None:
    """Test pressing the API buttons."""
    await setup_platform(menuai, [Platform.BUTTON])

    with patch(
        f"tesla_fleet_api.teslemetry.Vehicle.{func}",
        return_value=COMMAND_OK,
    ) as command:
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [f"button.test_{name}"]},
            blocking=True,
        )
        command.assert_called_once()
