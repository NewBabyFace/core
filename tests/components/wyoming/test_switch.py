"""Test Wyoming switch devices."""

from menuai.components.wyoming.devices import SatelliteDevice
from menuai.config_entries import ConfigEntry
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai

from . import reload_satellite


async def test_muted(
    menuai: menuai,
    satellite_config_entry: ConfigEntry,
    satellite_device: SatelliteDevice,
) -> None:
    """Test satellite muted."""
    muted_id = satellite_device.get_muted_entity_id(menuai)
    assert muted_id

    state = menuai.states.get(muted_id)
    assert state is not None
    assert state.state == STATE_OFF
    assert not satellite_device.is_muted

    await menuai.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": muted_id},
        blocking=True,
    )

    state = menuai.states.get(muted_id)
    assert state is not None
    assert state.state == STATE_ON
    assert satellite_device.is_muted

    # test restore
    satellite_device = await reload_satellite(menuai, satellite_config_entry.entry_id)

    state = menuai.states.get(muted_id)
    assert state is not None
    assert state.state == STATE_ON
    assert satellite_device.is_muted
