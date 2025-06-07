"""Tests for number entities provided by the Tailwind integration."""

from unittest.mock import MagicMock

from gotailwind import TailwindError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components import number
from menuai.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from menuai.components.tailwind.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr, entity_registry as er

pytestmark = pytest.mark.usefixtures("init_integration")


async def test_number_entities(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_tailwind: MagicMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test number entities provided by the Tailwind integration."""
    assert (state := menuai.states.get("number.tailwind_iq3_status_led_brightness"))
    assert snapshot == state

    assert (entity_entry := entity_registry.async_get(state.entity_id))
    assert snapshot == entity_entry

    assert entity_entry.device_id
    assert (device_entry := device_registry.async_get(entity_entry.device_id))
    assert snapshot == device_entry

    assert len(mock_tailwind.status_led.mock_calls) == 0
    await menuai.services.async_call(
        number.DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: state.entity_id,
            ATTR_VALUE: 42,
        },
        blocking=True,
    )

    assert len(mock_tailwind.status_led.mock_calls) == 1
    mock_tailwind.status_led.assert_called_with(brightness=42)

    # Test error handling
    mock_tailwind.status_led.side_effect = TailwindError("Some error")

    with pytest.raises(menuaiError) as excinfo:
        await menuai.services.async_call(
            number.DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: state.entity_id,
                ATTR_VALUE: 42,
            },
            blocking=True,
        )

    assert (
        str(excinfo.value)
        == "An error occurred while communicating with the Tailwind device"
    )
    assert excinfo.value.translation_domain == DOMAIN
    assert excinfo.value.translation_key == "communication_error"
