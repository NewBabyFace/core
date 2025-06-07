"""The tests for the demo sensor component."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai import core as ha
from menuai.components.demo import DOMAIN
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import mock_restore_cache_with_extra_data


@pytest.fixture(autouse=True)
async def sensor_only() -> None:
    """Enable only the sensor platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.SENSOR],
    ):
        yield


@pytest.mark.parametrize(("entity_id", "delta"), [("sensor.total_energy_kwh", 0.5)])
async def test_energy_sensor(
    menuai: menuai, entity_id, delta, freezer: FrozenDateTimeFactory
) -> None:
    """Test energy sensors increase periodically."""
    assert await async_setup_component(
        menuai, SENSOR_DOMAIN, {SENSOR_DOMAIN: {"platform": DOMAIN}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == "0"

    freezer.tick(timedelta(minutes=5, seconds=1))
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == str(delta)


@pytest.mark.parametrize(("entity_id", "delta"), [("sensor.total_energy_kwh", 0.5)])
async def test_restore_state(
    menuai: menuai, entity_id, delta, freezer: FrozenDateTimeFactory
) -> None:
    """Test energy sensors restore state."""
    fake_state = ha.State(
        entity_id,
        "",
    )
    fake_extra_data = {
        "native_value": 2**20,
        "native_unit_of_measurement": None,
    }
    mock_restore_cache_with_extra_data(menuai, ((fake_state, fake_extra_data),))

    assert await async_setup_component(
        menuai, SENSOR_DOMAIN, {SENSOR_DOMAIN: {"platform": DOMAIN}}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == str(2**20)

    freezer.tick(timedelta(minutes=5, seconds=1))
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == str(2**20 + delta)
