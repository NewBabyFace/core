"""Test VoIP select."""

from menuai.components.voip.devices import VoIPDevice
from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def test_pipeline_select(
    menuai: menuai,
    config_entry: ConfigEntry,
    voip_device: VoIPDevice,
) -> None:
    """Test pipeline select.

    Functionality is tested in assist_pipeline/test_select.py.
    This test is only to ensure it is set up.
    """
    state = menuai.states.get("select.192_168_1_210_assistant")
    assert state is not None
    assert state.state == "preferred"


async def test_vad_sensitivity_select(
    menuai: menuai,
    config_entry: ConfigEntry,
    voip_device: VoIPDevice,
) -> None:
    """Test VAD sensitivity select.

    Functionality is tested in assist_pipeline/test_select.py.
    This test is only to ensure it is set up.
    """
    state = menuai.states.get("select.192_168_1_210_finished_speaking_detection")
    assert state is not None
    assert state.state == "default"
