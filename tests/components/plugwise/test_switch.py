"""Tests for the Plugwise switch integration."""

from unittest.mock import MagicMock

from plugwise.exceptions import PlugwiseException
import pytest

from menuai.components.plugwise.const import DOMAIN
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_adam_climate_switch_entities(
    menuai: menuai, mock_smile_adam: MagicMock, init_integration: MockConfigEntry
) -> None:
    """Test creation of climate related switch entities."""
    state = menuai.states.get("switch.cv_pomp_relay")
    assert state
    assert state.state == STATE_ON

    state = menuai.states.get("switch.fibaro_hc2_relay")
    assert state
    assert state.state == STATE_ON


async def test_adam_climate_switch_negative_testing(
    menuai: menuai, mock_smile_adam: MagicMock, init_integration: MockConfigEntry
) -> None:
    """Test exceptions of climate related switch entities."""
    mock_smile_adam.set_switch_state.side_effect = PlugwiseException

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "switch.cv_pomp_relay"},
            blocking=True,
        )

    assert mock_smile_adam.set_switch_state.call_count == 1
    mock_smile_adam.set_switch_state.assert_called_with(
        "78d1126fc4c743db81b61c20e88342a7", None, "relay", STATE_OFF
    )

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.fibaro_hc2_relay"},
            blocking=True,
        )

    assert mock_smile_adam.set_switch_state.call_count == 2
    mock_smile_adam.set_switch_state.assert_called_with(
        "a28f588dc4a049a483fd03a30361ad3a", None, "relay", STATE_ON
    )


async def test_adam_climate_switch_changes(
    menuai: menuai, mock_smile_adam: MagicMock, init_integration: MockConfigEntry
) -> None:
    """Test changing of climate related switch entities."""
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.cv_pomp_relay"},
        blocking=True,
    )

    assert mock_smile_adam.set_switch_state.call_count == 1
    mock_smile_adam.set_switch_state.assert_called_with(
        "78d1126fc4c743db81b61c20e88342a7", None, "relay", STATE_OFF
    )

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: "switch.fibaro_hc2_relay"},
        blocking=True,
    )

    assert mock_smile_adam.set_switch_state.call_count == 2
    mock_smile_adam.set_switch_state.assert_called_with(
        "a28f588dc4a049a483fd03a30361ad3a", None, "relay", STATE_OFF
    )

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.fibaro_hc2_relay"},
        blocking=True,
    )

    assert mock_smile_adam.set_switch_state.call_count == 3
    mock_smile_adam.set_switch_state.assert_called_with(
        "a28f588dc4a049a483fd03a30361ad3a", None, "relay", STATE_ON
    )


async def test_stretch_switch_entities(
    menuai: menuai, mock_stretch: MagicMock, init_integration: MockConfigEntry
) -> None:
    """Test creation of climate related switch entities."""
    state = menuai.states.get("switch.koelkast_92c4a_relay")
    assert state
    assert state.state == STATE_ON

    state = menuai.states.get("switch.droger_52559_relay")
    assert state
    assert state.state == STATE_ON


async def test_stretch_switch_changes(
    menuai: menuai, mock_stretch: MagicMock, init_integration: MockConfigEntry
) -> None:
    """Test changing of power related switch entities."""
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.koelkast_92c4a_relay"},
        blocking=True,
    )
    assert mock_stretch.set_switch_state.call_count == 1
    mock_stretch.set_switch_state.assert_called_with(
        "e1c884e7dede431dadee09506ec4f859", None, "relay", STATE_OFF
    )

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TOGGLE,
        {ATTR_ENTITY_ID: "switch.droger_52559_relay"},
        blocking=True,
    )
    assert mock_stretch.set_switch_state.call_count == 2
    mock_stretch.set_switch_state.assert_called_with(
        "cfe95cf3de1948c0b8955125bf754614", None, "relay", STATE_OFF
    )

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.droger_52559_relay"},
        blocking=True,
    )
    assert mock_stretch.set_switch_state.call_count == 3
    mock_stretch.set_switch_state.assert_called_with(
        "cfe95cf3de1948c0b8955125bf754614", None, "relay", STATE_ON
    )


async def test_unique_id_migration_plug_relay(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_smile_adam: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test unique ID migration of -plugs to -relay."""
    mock_config_entry.add_to_menuai(menuai)

    # Entry to migrate
    entity_registry.async_get_or_create(
        SWITCH_DOMAIN,
        DOMAIN,
        "21f2b542c49845e6bb416884c55778d6-plug",
        config_entry=mock_config_entry,
        suggested_object_id="playstation_smart_plug",
        disabled_by=None,
    )
    # Entry not needing migration
    entity_registry.async_get_or_create(
        SWITCH_DOMAIN,
        DOMAIN,
        "675416a629f343c495449970e2ca37b5-relay",
        config_entry=mock_config_entry,
        suggested_object_id="ziggo_modem",
        disabled_by=None,
    )

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("switch.playstation_smart_plug") is not None
    assert menuai.states.get("switch.ziggo_modem") is not None

    entity_entry = entity_registry.async_get("switch.playstation_smart_plug")
    assert entity_entry
    assert entity_entry.unique_id == "21f2b542c49845e6bb416884c55778d6-relay"

    entity_entry = entity_registry.async_get("switch.ziggo_modem")
    assert entity_entry
    assert entity_entry.unique_id == "675416a629f343c495449970e2ca37b5-relay"
