"""Test Wyoming select."""

from unittest.mock import Mock, patch

from menuai.components import assist_pipeline
from menuai.components.assist_pipeline.pipeline import PipelineData
from menuai.components.assist_pipeline.select import OPTION_PREFERRED
from menuai.components.assist_pipeline.vad import VadSensitivity
from menuai.components.wyoming.devices import SatelliteDevice
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import reload_satellite


async def test_pipeline_select(
    menuai: menuai,
    satellite_config_entry: ConfigEntry,
    satellite_device: SatelliteDevice,
) -> None:
    """Test pipeline select.

    Functionality is tested in assist_pipeline/test_select.py.
    This test is only to ensure it is set up.
    """
    assert await async_setup_component(menuai, assist_pipeline.DOMAIN, {})
    pipeline_data: PipelineData = menuai.data[assist_pipeline.DOMAIN]

    # Create second pipeline
    await pipeline_data.pipeline_store.async_create_item(
        {
            "name": "Test 1",
            "language": "en-US",
            "conversation_engine": None,
            "conversation_language": "en-US",
            "tts_engine": None,
            "tts_language": None,
            "tts_voice": None,
            "stt_engine": None,
            "stt_language": None,
            "wake_word_entity": None,
            "wake_word_id": None,
        }
    )

    # Preferred pipeline is the default
    pipeline_entity_id = satellite_device.get_pipeline_entity_id(menuai)
    assert pipeline_entity_id

    state = menuai.states.get(pipeline_entity_id)
    assert state is not None
    assert state.state == OPTION_PREFERRED

    # Change to second pipeline
    with patch.object(satellite_device, "set_pipeline_name") as mock_pipeline_changed:
        await menuai.services.async_call(
            "select",
            "select_option",
            {"entity_id": pipeline_entity_id, "option": "Test 1"},
            blocking=True,
        )

        state = menuai.states.get(pipeline_entity_id)
        assert state is not None
        assert state.state == "Test 1"

        # set function should have been called
        mock_pipeline_changed.assert_called_once_with("Test 1")

    # test restore
    satellite_device = await reload_satellite(menuai, satellite_config_entry.entry_id)

    state = menuai.states.get(pipeline_entity_id)
    assert state is not None
    assert state.state == "Test 1"

    # Change back and check update listener
    pipeline_listener = Mock()
    satellite_device.set_pipeline_listener(pipeline_listener)

    await menuai.services.async_call(
        "select",
        "select_option",
        {"entity_id": pipeline_entity_id, "option": OPTION_PREFERRED},
        blocking=True,
    )

    state = menuai.states.get(pipeline_entity_id)
    assert state is not None
    assert state.state == OPTION_PREFERRED

    # listener should have been called
    pipeline_listener.assert_called_once()


async def test_noise_suppression_level_select(
    menuai: menuai,
    satellite_config_entry: ConfigEntry,
    satellite_device: SatelliteDevice,
) -> None:
    """Test noise suppression level select."""
    nsl_entity_id = satellite_device.get_noise_suppression_level_entity_id(menuai)
    assert nsl_entity_id

    state = menuai.states.get(nsl_entity_id)
    assert state is not None
    assert state.state == "off"
    assert satellite_device.noise_suppression_level == 0

    # Change setting
    with patch.object(
        satellite_device, "set_noise_suppression_level"
    ) as mock_nsl_changed:
        await menuai.services.async_call(
            "select",
            "select_option",
            {"entity_id": nsl_entity_id, "option": "max"},
            blocking=True,
        )

        state = menuai.states.get(nsl_entity_id)
        assert state is not None
        assert state.state == "max"

        # set function should have been called
        mock_nsl_changed.assert_called_once_with(4)

    # test restore
    satellite_device = await reload_satellite(menuai, satellite_config_entry.entry_id)

    state = menuai.states.get(nsl_entity_id)
    assert state is not None
    assert state.state == "max"

    await menuai.services.async_call(
        "select",
        "select_option",
        {"entity_id": nsl_entity_id, "option": "medium"},
        blocking=True,
    )

    assert satellite_device.noise_suppression_level == 2


async def test_vad_sensitivity_select(
    menuai: menuai,
    satellite_config_entry: ConfigEntry,
    satellite_device: SatelliteDevice,
) -> None:
    """Test VAD sensitivity select."""
    vs_entity_id = satellite_device.get_vad_sensitivity_entity_id(menuai)
    assert vs_entity_id

    state = menuai.states.get(vs_entity_id)
    assert state is not None
    assert state.state == VadSensitivity.DEFAULT
    assert satellite_device.vad_sensitivity == VadSensitivity.DEFAULT

    # Change setting
    with patch.object(satellite_device, "set_vad_sensitivity") as mock_vs_changed:
        await menuai.services.async_call(
            "select",
            "select_option",
            {"entity_id": vs_entity_id, "option": VadSensitivity.AGGRESSIVE.value},
            blocking=True,
        )

        state = menuai.states.get(vs_entity_id)
        assert state is not None
        assert state.state == VadSensitivity.AGGRESSIVE.value

        # set function should have been called
        mock_vs_changed.assert_called_once_with(VadSensitivity.AGGRESSIVE)

    # test restore
    satellite_device = await reload_satellite(menuai, satellite_config_entry.entry_id)

    state = menuai.states.get(vs_entity_id)
    assert state is not None
    assert state.state == VadSensitivity.AGGRESSIVE.value

    await menuai.services.async_call(
        "select",
        "select_option",
        {"entity_id": vs_entity_id, "option": VadSensitivity.RELAXED.value},
        blocking=True,
    )

    assert satellite_device.vad_sensitivity == VadSensitivity.RELAXED
