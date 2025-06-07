"""Test VoIP switch devices."""

from menuai.components.voip.devices import VoIPDevice
from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def test_allow_call(
    menuai: menuai,
    config_entry: ConfigEntry,
    voip_device: VoIPDevice,
) -> None:
    """Test allow call."""
    assert not voip_device.async_allow_call(menuai)

    state = menuai.states.get("switch.192_168_1_210_allow_calls")
    assert state is not None
    assert state.state == "off"

    await menuai.config_entries.async_reload(config_entry.entry_id)

    state = menuai.states.get("switch.192_168_1_210_allow_calls")
    assert state.state == "off"

    await menuai.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.192_168_1_210_allow_calls"},
        blocking=True,
    )

    assert voip_device.async_allow_call(menuai)

    state = menuai.states.get("switch.192_168_1_210_allow_calls")
    assert state.state == "on"

    await menuai.config_entries.async_reload(config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.192_168_1_210_allow_calls")
    assert state.state == "on"

    await menuai.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.192_168_1_210_allow_calls"},
        blocking=True,
    )

    assert not voip_device.async_allow_call(menuai)

    state = menuai.states.get("switch.192_168_1_210_allow_calls")
    assert state.state == "off"
