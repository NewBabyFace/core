"""Test the SmartTub switch platform."""

import pytest

from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai


@pytest.mark.parametrize(
    ("pump_id", "entity_suffix", "pump_state"),
    [
        ("CP", "circulation_pump", "off"),
        ("P1", "jet_p1", "off"),
        ("P2", "jet_p2", "on"),
    ],
)
async def test_pumps(
    spa, setup_entry, menuai: menuai, pump_id, pump_state, entity_suffix
) -> None:
    """Test pump entities."""

    status = await spa.get_status_full()
    pump = next(pump for pump in status.pumps if pump.id == pump_id)

    entity_id = f"switch.{spa.brand}_{spa.model}_{entity_suffix}"
    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == pump_state

    await menuai.services.async_call(
        "switch",
        "toggle",
        {"entity_id": entity_id},
        blocking=True,
    )
    pump.toggle.assert_called()

    if state.state == STATE_OFF:
        await menuai.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": entity_id},
            blocking=True,
        )
        pump.toggle.assert_called()
    else:
        assert state.state == STATE_ON

        await menuai.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": entity_id},
            blocking=True,
        )
        pump.toggle.assert_called()
