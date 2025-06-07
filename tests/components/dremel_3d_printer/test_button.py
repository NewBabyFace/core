"""Button tests for the Dremel 3D Printer integration."""

from unittest.mock import patch

import pytest

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.dremel_3d_printer.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("button", "function"),
    [
        ("cancel", "stop"),
        ("pause", "pause"),
        ("resume", "resume"),
    ],
)
@pytest.mark.usefixtures("connection", "entity_registry_enabled_by_default")
async def test_buttons(
    menuai: menuai,
    config_entry: MockConfigEntry,
    button: str,
    function: str,
) -> None:
    """Test button entities function."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    assert await async_setup_component(menuai, DOMAIN, {})
    with patch(
        f"menuai.components.dremel_3d_printer.Dremel3DPrinter.{function}_print"
    ) as mock:
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [f"button.dremel_3d45_{button}_job"]},
            blocking=True,
        )
    assert mock.call_count == 1

    with (
        patch(
            f"menuai.components.dremel_3d_printer.Dremel3DPrinter.{function}_print",
            side_effect=RuntimeError,
        ) as mock,
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: [f"button.dremel_3d45_{button}_job"]},
            blocking=True,
        )
    assert mock.call_count == 1
