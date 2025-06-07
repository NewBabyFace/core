"""The tests for the date component."""

from datetime import date

from menuai.components.date import DOMAIN, SERVICE_SET_VALUE
from menuai.const import (
    ATTR_DATE,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    CONF_PLATFORM,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

from .common import MockDateEntity

from tests.common import setup_test_component_platform


async def test_date(menuai: menuai) -> None:
    """Test date entity."""
    entity = MockDateEntity(
        name="test",
        unique_id="unique_date",
        native_value=date(2020, 1, 1),
    )
    setup_test_component_platform(menuai, DOMAIN, [entity])

    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})
    await menuai.async_block_till_done()

    state = menuai.states.get("date.test")
    assert state.state == "2020-01-01"
    assert state.attributes == {ATTR_FRIENDLY_NAME: "test"}

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_DATE: date(2021, 1, 1), ATTR_ENTITY_ID: "date.test"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("date.test")
    assert state.state == "2021-01-01"

    date_entity = MockDateEntity(native_value=None)
    assert date_entity.state is None
    assert date_entity.state_attributes is None
