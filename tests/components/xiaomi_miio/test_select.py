"""The tests for the xiaomi_miio select component."""

from unittest.mock import MagicMock, patch

from arrow import utcnow
from miio.integrations.airpurifier.dmaker.airfresh_t2017 import (
    DisplayOrientation,
    PtcLevel,
)
import pytest

from menuai.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.components.xiaomi_miio import UPDATE_INTERVAL
from menuai.components.xiaomi_miio.const import (
    CONF_FLOW_TYPE,
    DOMAIN,
    MODEL_AIRFRESH_T2017,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MAC,
    CONF_MODEL,
    CONF_TOKEN,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError

from . import TEST_MAC

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.fixture(autouse=True)
async def setup_test(menuai: menuai):
    """Initialize test xiaomi_miio for select entity."""

    mock_airfresh = MagicMock()
    mock_airfresh.status().display_orientation = DisplayOrientation.Portrait
    mock_airfresh.status().ptc_level = PtcLevel.Low

    with (
        patch(
            "menuai.components.xiaomi_miio.get_platforms",
            return_value=[
                Platform.SELECT,
            ],
        ),
        patch(
            "menuai.components.xiaomi_miio.AirFreshT2017"
        ) as mock_airfresh_cls,
    ):
        mock_airfresh_cls.return_value = mock_airfresh
        yield mock_airfresh


async def test_select_params(menuai: menuai) -> None:
    """Test the initial parameters."""

    entity_name = "test_airfresh_select"
    entity_id = await setup_component(menuai, entity_name)

    select_entity = menuai.states.get(entity_id + "_display_orientation")
    assert select_entity
    assert select_entity.state == "forward"
    assert select_entity.attributes.get(ATTR_OPTIONS) == ["forward", "left", "right"]


async def test_select_bad_attr(menuai: menuai) -> None:
    """Test selecting a different option with invalid option value."""

    entity_name = "test_airfresh_select"
    entity_id = await setup_component(menuai, entity_name)

    state = menuai.states.get(entity_id + "_display_orientation")
    assert state
    assert state.state == "forward"

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            "select",
            SERVICE_SELECT_OPTION,
            {ATTR_OPTION: "up", ATTR_ENTITY_ID: entity_id + "_display_orientation"},
            blocking=True,
        )
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id + "_display_orientation")
    assert state
    assert state.state == "forward"


async def test_select_option(menuai: menuai) -> None:
    """Test selecting of a option."""

    entity_name = "test_airfresh_select"
    entity_id = await setup_component(menuai, entity_name)

    state = menuai.states.get(entity_id + "_display_orientation")
    assert state
    assert state.state == "forward"

    await menuai.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        {ATTR_OPTION: "left", ATTR_ENTITY_ID: entity_id + "_display_orientation"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id + "_display_orientation")
    assert state
    assert state.state == "left"


async def test_select_coordinator_update(menuai: menuai, setup_test) -> None:
    """Test coordinator update of a option."""

    entity_name = "test_airfresh_select"
    entity_id = await setup_component(menuai, entity_name)

    state = menuai.states.get(entity_id + "_display_orientation")
    assert state
    assert state.state == "forward"

    # emulate someone change state from device maybe used app
    setup_test.status().display_orientation = DisplayOrientation.LandscapeLeft

    async_fire_time_changed(menuai, utcnow() + UPDATE_INTERVAL)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id + "_display_orientation")
    assert state
    assert state.state == "left"


async def setup_component(menuai: menuai, entity_name: str) -> str:
    """Set up component."""
    entity_id = f"{SELECT_DOMAIN}.{entity_name}"

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="123456",
        title=entity_name,
        data={
            CONF_FLOW_TYPE: CONF_DEVICE,
            CONF_HOST: "0.0.0.0",
            CONF_TOKEN: "12345678901234567890123456789012",
            CONF_MODEL: MODEL_AIRFRESH_T2017,
            CONF_MAC: TEST_MAC,
        },
    )

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    return entity_id
