"""Tests for HomematicIP Cloud button."""

from freezegun.api import FrozenDateTimeFactory

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from menuai.core import menuai
from menuai.util import dt as dt_util

from .helper import HomeFactory, get_and_check_entity_basics


async def test_hmip_garage_door_controller_button(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    default_mock_hap_factory: HomeFactory,
) -> None:
    """Test HomematicipGarageDoorControllerButton."""
    entity_id = "button.garagentor"
    entity_name = "Garagentor"
    device_model = "HmIP-WGC"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=[entity_name]
    )

    get_and_check_entity_basics(menuai, mock_hap, entity_id, entity_name, device_model)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_UNKNOWN

    now = dt_util.parse_datetime("2021-01-09 12:00:00+00:00")
    freezer.move_to(now)
    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == now.isoformat()
