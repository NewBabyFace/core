"""Switch tests for the D-Link Smart Plug integration."""

from unittest.mock import patch

from menuai.components.dlink.const import DOMAIN
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai

from .conftest import CONF_DATA

from tests.common import AsyncMock, MockConfigEntry


async def test_switch_state(menuai: menuai, mocked_plug: AsyncMock) -> None:
    """Test we get the switch status."""
    with patch(
        "menuai.components.dlink.SmartPlug",
        return_value=mocked_plug,
    ):
        entry = MockConfigEntry(domain=DOMAIN, data=CONF_DATA)
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    entity_id = "switch.mock_title"
    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF
    assert state.attributes["total_consumption"] == 1040.0
    assert state.attributes["temperature"] == 33
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    assert menuai.states.get(entity_id).state == STATE_ON
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    assert menuai.states.get(entity_id).state == STATE_OFF


async def test_switch_no_value(
    menuai: menuai, mocked_plug_legacy: AsyncMock
) -> None:
    """Test we handle 'N/A' being passed by the pypi package."""
    with patch(
        "menuai.components.dlink.SmartPlug",
        return_value=mocked_plug_legacy,
    ):
        entry = MockConfigEntry(domain=DOMAIN, data=CONF_DATA)
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("switch.mock_title")
    assert state.state == STATE_OFF
    assert state.attributes["total_consumption"] is None
    assert state.attributes["temperature"] is None
