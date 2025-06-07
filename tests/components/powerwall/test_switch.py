"""Test for Powerwall off-grid switch."""

from unittest.mock import MagicMock, patch

import pytest
from tesla_powerwall import GridStatus, PowerwallError

from menuai.components.powerwall.const import DOMAIN
from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, CONF_IP_ADDRESS, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from .mocks import _mock_powerwall_with_fixtures

from tests.common import MockConfigEntry

ENTITY_ID = "switch.mysite_off_grid_operation"


@pytest.fixture(name="mock_powerwall")
async def mock_powerwall_fixture(menuai: menuai) -> MagicMock:
    """Set up base powerwall fixture."""

    mock_powerwall = await _mock_powerwall_with_fixtures(menuai)

    config_entry = MockConfigEntry(domain=DOMAIN, data={CONF_IP_ADDRESS: "1.2.3.4"})
    config_entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.powerwall.Powerwall", return_value=mock_powerwall
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        yield mock_powerwall


async def test_entity_registry(
    menuai: menuai, mock_powerwall, entity_registry: er.EntityRegistry
) -> None:
    """Test powerwall off-grid switch device."""

    mock_powerwall.get_grid_status.return_value = GridStatus.CONNECTED

    assert ENTITY_ID in entity_registry.entities


async def test_initial(menuai: menuai, mock_powerwall) -> None:
    """Test initial grid status without off grid switch selected."""

    mock_powerwall.get_grid_status.return_value = GridStatus.CONNECTED

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF


async def test_on(menuai: menuai, mock_powerwall) -> None:
    """Test state once offgrid switch has been turned on."""

    mock_powerwall.get_grid_status.return_value = GridStatus.ISLANDED

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_ON


async def test_off(menuai: menuai, mock_powerwall) -> None:
    """Test state once offgrid switch has been turned off."""

    mock_powerwall.get_grid_status.return_value = GridStatus.CONNECTED

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )

    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF


async def test_exception_on_powerwall_error(
    menuai: menuai, mock_powerwall
) -> None:
    """Ensure that an exception in the tesla_powerwall library causes a menuaiError."""

    mock_powerwall.set_island_mode.side_effect = PowerwallError("Mock exception")
    with pytest.raises(menuaiError, match="Setting off-grid operation to"):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
