"""Test the Tessie button platform."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import assert_entities, setup_platform


async def test_buttons(
    menuai: menuai, snapshot: SnapshotAssertion, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the button entities are correct."""

    entry = await setup_platform(menuai, [Platform.BUTTON])

    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)

    for entity_id, func in (
        ("button.test_wake", "wake"),
        ("button.test_flash_lights", "flash_lights"),
        ("button.test_honk_horn", "honk"),
        ("button.test_homelink", "trigger_homelink"),
        ("button.test_keyless_driving", "enable_keyless_driving"),
        ("button.test_play_fart", "boombox"),
    ):
        with patch(
            f"menuai.components.tessie.button.{func}",
        ) as mock_press:
            await menuai.services.async_call(
                BUTTON_DOMAIN,
                SERVICE_PRESS,
                {ATTR_ENTITY_ID: [entity_id]},
                blocking=True,
            )
            mock_press.assert_called_once()
