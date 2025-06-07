"""Test the generic hygrostat config flow."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.climate import PRESET_AWAY
from menuai.components.generic_thermostat.const import (
    CONF_AC_MODE,
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_PRESETS,
    CONF_SENSOR,
    DOMAIN,
)
from menuai.components.sensor import SensorDeviceClass
from menuai.config_entries import SOURCE_USER
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME,
    STATE_OFF,
    UnitOfTemperature,
)
from menuai.core import menuai

from tests.common import MockConfigEntry

SNAPSHOT_FLOW_PROPS = props("type", "title", "result", "error")


async def test_config_flow(menuai: menuai, snapshot: SnapshotAssertion) -> None:
    """Test the config flow."""
    with patch(
        "menuai.components.generic_thermostat.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result == snapshot(name="init", include=SNAPSHOT_FLOW_PROPS)

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "My thermostat",
                CONF_HEATER: "switch.run",
                CONF_SENSOR: "sensor.temperature",
                CONF_AC_MODE: False,
                CONF_COLD_TOLERANCE: 0.3,
                CONF_HOT_TOLERANCE: 0.3,
            },
        )
        assert result == snapshot(name="presets", include=SNAPSHOT_FLOW_PROPS)

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_PRESETS[PRESET_AWAY]: 20,
            },
        )
        assert result == snapshot(name="create_entry", include=SNAPSHOT_FLOW_PROPS)

        await menuai.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.title == "My thermostat"


async def test_options(menuai: menuai, snapshot: SnapshotAssertion) -> None:
    """Test reconfiguring."""

    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_NAME: "My thermostat",
            CONF_HEATER: "switch.run",
            CONF_SENSOR: "sensor.temperature",
            CONF_AC_MODE: False,
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            CONF_PRESETS[PRESET_AWAY]: 20,
        },
        title="My dehumidifier",
    )
    config_entry.add_to_menuai(menuai)

    menuai.states.async_set(
        "sensor.temperature",
        "15",
        {
            ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.CELSIUS,
            ATTR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
        },
    )
    menuai.states.async_set("switch.run", STATE_OFF)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    # check that it is setup
    await menuai.async_block_till_done()
    assert menuai.states.get("climate.my_thermostat") == snapshot(name="with_away")

    # remove away preset
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result == snapshot(name="init", include=SNAPSHOT_FLOW_PROPS)

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HEATER: "switch.run",
            CONF_SENSOR: "sensor.temperature",
            CONF_AC_MODE: False,
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        },
    )
    assert result == snapshot(name="presets", include=SNAPSHOT_FLOW_PROPS)

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result == snapshot(name="create_entry", include=SNAPSHOT_FLOW_PROPS)

    # Check config entry is reloaded with new options
    await menuai.async_block_till_done()
    assert menuai.states.get("climate.my_thermostat") == snapshot(name="without_away")


async def test_config_flow_preset_accepts_float(
    menuai: menuai, snapshot: SnapshotAssertion
) -> None:
    """Test the config flow with preset is a float."""
    with patch(
        "menuai.components.generic_thermostat.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result == snapshot(name="init", include=SNAPSHOT_FLOW_PROPS)

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "My thermostat",
                CONF_HEATER: "switch.run",
                CONF_SENSOR: "sensor.temperature",
                CONF_AC_MODE: False,
                CONF_COLD_TOLERANCE: 0.3,
                CONF_HOT_TOLERANCE: 0.3,
            },
        )
        assert result == snapshot(name="presets", include=SNAPSHOT_FLOW_PROPS)

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_PRESETS[PRESET_AWAY]: 10.4,
            },
        )
        assert result == snapshot(name="create_entry", include=SNAPSHOT_FLOW_PROPS)

        await menuai.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 1
    assert result["options"] == {
        "ac_mode": False,
        "away_temp": 10.4,
        "cold_tolerance": 0.3,
        "heater": "switch.run",
        "hot_tolerance": 0.3,
        "name": "My thermostat",
        "target_sensor": "sensor.temperature",
    }
