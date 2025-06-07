"""Tests for button entities provided by the Tailwind integration."""

from unittest.mock import MagicMock

from gotailwind import TailwindError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.tailwind.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr, entity_registry as er

pytestmark = [
    pytest.mark.usefixtures("init_integration"),
    pytest.mark.freeze_time("2023-12-17 15:25:00"),
]


async def test_number_entities(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_tailwind: MagicMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test button entities provided by the Tailwind integration."""
    assert (state := menuai.states.get("button.tailwind_iq3_identify"))
    assert snapshot == state

    assert (entity_entry := entity_registry.async_get(state.entity_id))
    assert snapshot == entity_entry

    assert entity_entry.device_id
    assert (device_entry := device_registry.async_get(entity_entry.device_id))
    assert snapshot == device_entry

    assert len(mock_tailwind.identify.mock_calls) == 0
    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: state.entity_id},
        blocking=True,
    )

    assert len(mock_tailwind.identify.mock_calls) == 1
    mock_tailwind.identify.assert_called_with()

    assert (state := menuai.states.get(state.entity_id))
    assert state.state == "2023-12-17T15:25:00+00:00"

    # Test error handling
    mock_tailwind.identify.side_effect = TailwindError("Some error")

    with pytest.raises(menuaiError, match="Some error") as excinfo:
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: state.entity_id},
            blocking=True,
        )

    assert excinfo.value.translation_domain == DOMAIN
    assert excinfo.value.translation_key == "communication_error"
