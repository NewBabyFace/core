"""The tests for the Rfxtrx siren platform."""

from unittest.mock import call

from menuai.components.rfxtrx import DOMAIN
from menuai.core import menuai

from .conftest import create_rfx_test_cfg

from tests.common import MockConfigEntry


async def test_one_chime(menuai: menuai, rfxtrx, timestep) -> None:
    """Test with 1 entity."""
    entry_data = create_rfx_test_cfg(
        devices={"0a16000000000000000000": {"off_delay": 2.0}}
    )
    mock_entry = MockConfigEntry(domain="rfxtrx", unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_menuai(menuai)

    entity_id = "siren.byron_sx_00_00"

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "Byron SX 00:00"

    await menuai.services.async_call(
        "siren", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    state = menuai.states.get(entity_id)
    assert state.state == "on"

    await timestep(5)

    state = menuai.states.get(entity_id)
    assert state.state == "off"

    await menuai.services.async_call(
        "siren", "turn_on", {"entity_id": entity_id, "tone": "Sound 1"}, blocking=True
    )
    state = menuai.states.get(entity_id)
    assert state.state == "on"

    await timestep(3)

    state = menuai.states.get(entity_id)
    assert state.state == "off"

    await rfxtrx.signal("0a16000000000000000000")
    state = menuai.states.get(entity_id)
    assert state.state == "on"

    await timestep(3)

    state = menuai.states.get(entity_id)
    assert state.state == "off"

    assert rfxtrx.transport.send.mock_calls == [
        call(bytearray(b"\x07\x16\x00\x00\x00\x00\x00\x00")),
        call(bytearray(b"\x07\x16\x00\x00\x00\x00\x01\x00")),
    ]


async def test_one_security1(menuai: menuai, rfxtrx, timestep) -> None:
    """Test with 1 entity."""
    entry_data = create_rfx_test_cfg(devices={"08200300a109000670": {"off_delay": 2.0}})
    mock_entry = MockConfigEntry(domain="rfxtrx", unique_id=DOMAIN, data=entry_data)

    mock_entry.add_to_menuai(menuai)

    entity_id = "siren.kd101_smoke_detector_a10900_32"

    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "KD101 Smoke Detector a10900:32"

    await menuai.services.async_call(
        "siren", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    state = menuai.states.get(entity_id)
    assert state.state == "on"

    await menuai.services.async_call(
        "siren", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    state = menuai.states.get(entity_id)
    assert state.state == "off"

    await menuai.services.async_call(
        "siren", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    state = menuai.states.get(entity_id)
    assert state.state == "on"

    await timestep(11)

    state = menuai.states.get(entity_id)
    assert state.state == "off"

    await rfxtrx.signal("08200300a109000670")
    state = menuai.states.get(entity_id)
    assert state.state == "on"

    await rfxtrx.signal("08200300a109000770")
    state = menuai.states.get(entity_id)
    assert state.state == "off"

    assert rfxtrx.transport.send.mock_calls == [
        call(bytearray(b"\x08\x20\x03\x00\xa1\x09\x00\x06\x00")),
        call(bytearray(b"\x08\x20\x03\x01\xa1\x09\x00\x07\x00")),
        call(bytearray(b"\x08\x20\x03\x02\xa1\x09\x00\x06\x00")),
    ]


async def test_discover_siren(menuai: menuai, rfxtrx_automatic) -> None:
    """Test with discovery."""
    rfxtrx = rfxtrx_automatic

    await rfxtrx.signal("0a16000000000000000000")
    state = menuai.states.get("siren.byron_sx_00_00")
    assert state
    assert state.state == "on"
    assert state.attributes.get("friendly_name") == "Byron SX 00:00"

    await rfxtrx.signal("0a16010000000000000000")
    state = menuai.states.get("siren.byron_mp001_00_00")
    assert state
    assert state.state == "on"
    assert state.attributes.get("friendly_name") == "Byron MP001 00:00"
