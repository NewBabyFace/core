"""Test cases for the sensors of the Huisbaasje integration."""

from unittest.mock import patch

from menuai.components.huisbaasje.const import DOMAIN
from menuai.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ID,
    CONF_PASSWORD,
    CONF_USERNAME,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from menuai.core import menuai

from .test_data import MOCK_CURRENT_MEASUREMENTS, MOCK_LIMITED_CURRENT_MEASUREMENTS

from tests.common import MockConfigEntry


async def test_setup_entry(menuai: menuai) -> None:
    """Test for successfully loading sensor states."""
    with (
        patch(
            "energyflip.EnergyFlip.authenticate", return_value=None
        ) as mock_authenticate,
        patch(
            "energyflip.EnergyFlip.is_authenticated", return_value=True
        ) as mock_is_authenticated,
        patch(
            "energyflip.EnergyFlip.current_measurements",
            return_value=MOCK_CURRENT_MEASUREMENTS,
        ) as mock_current_measurements,
    ):
        config_entry = MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="userId",
            data={
                CONF_ID: "userId",
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
            source="test",
        )
        config_entry.add_to_menuai(menuai)

        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        # Assert data is loaded
        current_power = menuai.states.get("sensor.current_power")
        assert current_power.state == "1011.66666666667"
        assert (
            current_power.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.POWER
        )
        assert (
            current_power.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.MEASUREMENT
        )
        assert (
            current_power.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfPower.WATT
        )

        current_power_in = menuai.states.get("sensor.current_power_in_peak")
        assert current_power_in.state == "1011.66666666667"
        assert (
            current_power_in.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.POWER
        )
        assert (
            current_power_in.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.MEASUREMENT
        )
        assert (
            current_power_in.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfPower.WATT
        )

        current_power_in_low = menuai.states.get("sensor.current_power_in_off_peak")
        assert current_power_in_low.state == "unknown"
        assert (
            current_power_in_low.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.POWER
        )
        assert (
            current_power_in_low.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.MEASUREMENT
        )
        assert (
            current_power_in_low.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfPower.WATT
        )

        current_power_out = menuai.states.get("sensor.current_power_out_peak")
        assert current_power_out.state == "unknown"
        assert (
            current_power_out.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.POWER
        )
        assert (
            current_power_out.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.MEASUREMENT
        )
        assert (
            current_power_out.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfPower.WATT
        )

        current_power_out_low = menuai.states.get("sensor.current_power_out_off_peak")
        assert current_power_out_low.state == "unknown"
        assert (
            current_power_out_low.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.POWER
        )
        assert (
            current_power_out_low.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.MEASUREMENT
        )
        assert (
            current_power_out_low.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfPower.WATT
        )

        energy_consumption_peak_today = menuai.states.get(
            "sensor.energy_consumption_peak_today"
        )
        assert energy_consumption_peak_today.state == "2.669999453"
        assert (
            energy_consumption_peak_today.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.ENERGY
        )
        assert (
            energy_consumption_peak_today.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.TOTAL_INCREASING
        )
        assert (
            energy_consumption_peak_today.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfEnergy.KILO_WATT_HOUR
        )

        energy_consumption_off_peak_today = menuai.states.get(
            "sensor.energy_consumption_off_peak_today"
        )
        assert energy_consumption_off_peak_today.state == "0.626666416"
        assert (
            energy_consumption_off_peak_today.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.ENERGY
        )
        assert (
            energy_consumption_off_peak_today.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.TOTAL_INCREASING
        )
        assert (
            energy_consumption_off_peak_today.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfEnergy.KILO_WATT_HOUR
        )

        energy_production_peak_today = menuai.states.get(
            "sensor.energy_production_peak_today"
        )
        assert energy_production_peak_today.state == "1.51234"
        assert (
            energy_production_peak_today.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.ENERGY
        )
        assert (
            energy_production_peak_today.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.TOTAL_INCREASING
        )
        assert (
            energy_production_peak_today.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfEnergy.KILO_WATT_HOUR
        )

        energy_production_off_peak_today = menuai.states.get(
            "sensor.energy_production_off_peak_today"
        )
        assert energy_production_off_peak_today.state == "1.09281"
        assert (
            energy_production_off_peak_today.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.ENERGY
        )
        assert (
            energy_production_off_peak_today.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.TOTAL_INCREASING
        )
        assert (
            energy_production_off_peak_today.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfEnergy.KILO_WATT_HOUR
        )

        energy_today = menuai.states.get("sensor.energy_today")
        assert energy_today.state == "3.296665869"
        assert (
            energy_today.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.ENERGY
        )
        assert energy_today.attributes.get(ATTR_STATE_CLASS) is SensorStateClass.TOTAL
        assert (
            energy_today.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfEnergy.KILO_WATT_HOUR
        )

        energy_this_week = menuai.states.get("sensor.energy_this_week")
        assert energy_this_week.state == "17.509996085"
        assert (
            energy_this_week.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.ENERGY
        )
        assert (
            energy_this_week.attributes.get(ATTR_STATE_CLASS) is SensorStateClass.TOTAL
        )
        assert (
            energy_this_week.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfEnergy.KILO_WATT_HOUR
        )

        energy_this_month = menuai.states.get("sensor.energy_this_month")
        assert energy_this_month.state == "103.28830788"
        assert (
            energy_this_month.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.ENERGY
        )
        assert (
            energy_this_month.attributes.get(ATTR_STATE_CLASS) is SensorStateClass.TOTAL
        )
        assert (
            energy_this_month.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfEnergy.KILO_WATT_HOUR
        )

        energy_this_year = menuai.states.get("sensor.energy_this_year")
        assert energy_this_year.state == "672.97811773"
        assert (
            energy_this_year.attributes.get(ATTR_DEVICE_CLASS)
            == SensorDeviceClass.ENERGY
        )
        assert (
            energy_this_year.attributes.get(ATTR_STATE_CLASS) is SensorStateClass.TOTAL
        )
        assert (
            energy_this_year.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfEnergy.KILO_WATT_HOUR
        )

        current_gas = menuai.states.get("sensor.current_gas")
        assert current_gas.state == "0.0"
        assert current_gas.attributes.get(ATTR_DEVICE_CLASS) is None
        assert (
            current_gas.attributes.get(ATTR_STATE_CLASS) is SensorStateClass.MEASUREMENT
        )
        assert (
            current_gas.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
        )

        gas_today = menuai.states.get("sensor.gas_today")
        assert gas_today.state == "1.07"
        assert gas_today.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.GAS
        assert (
            gas_today.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.TOTAL_INCREASING
        )
        assert (
            gas_today.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfVolume.CUBIC_METERS
        )

        gas_this_week = menuai.states.get("sensor.gas_this_week")
        assert gas_this_week.state == "5.634224386"
        assert gas_this_week.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.GAS
        assert (
            gas_this_week.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.TOTAL_INCREASING
        )
        assert (
            gas_this_week.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfVolume.CUBIC_METERS
        )

        gas_this_month = menuai.states.get("sensor.gas_this_month")
        assert gas_this_month.state == "39.14"
        assert gas_this_month.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.GAS
        assert (
            gas_this_month.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.TOTAL_INCREASING
        )
        assert (
            gas_this_month.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfVolume.CUBIC_METERS
        )

        gas_this_year = menuai.states.get("sensor.gas_this_year")
        assert gas_this_year.state == "116.73"
        assert gas_this_year.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.GAS
        assert (
            gas_this_year.attributes.get(ATTR_STATE_CLASS)
            is SensorStateClass.TOTAL_INCREASING
        )
        assert (
            gas_this_year.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            == UnitOfVolume.CUBIC_METERS
        )

        # Assert mocks are called
        assert len(mock_authenticate.mock_calls) == 1
        assert len(mock_is_authenticated.mock_calls) == 1
        assert len(mock_current_measurements.mock_calls) == 1


async def test_setup_entry_absent_measurement(menuai: menuai) -> None:
    """Test for successfully loading sensor states when response does not contain all measurements."""
    with (
        patch(
            "energyflip.EnergyFlip.authenticate", return_value=None
        ) as mock_authenticate,
        patch(
            "energyflip.EnergyFlip.is_authenticated", return_value=True
        ) as mock_is_authenticated,
        patch(
            "energyflip.EnergyFlip.current_measurements",
            return_value=MOCK_LIMITED_CURRENT_MEASUREMENTS,
        ) as mock_current_measurements,
    ):
        config_entry = MockConfigEntry(
            version=1,
            domain=DOMAIN,
            title="userId",
            data={
                CONF_ID: "userId",
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
            source="test",
        )
        config_entry.add_to_menuai(menuai)

        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        # Assert data is loaded
        assert menuai.states.get("sensor.current_power").state == "1011.66666666667"
        assert menuai.states.get("sensor.current_power_in_peak").state == "unknown"
        assert menuai.states.get("sensor.current_power_in_off_peak").state == "unknown"
        assert menuai.states.get("sensor.current_power_out_peak").state == "unknown"
        assert menuai.states.get("sensor.current_power_out_off_peak").state == "unknown"
        assert menuai.states.get("sensor.current_gas").state == "unknown"
        assert menuai.states.get("sensor.energy_today").state == "3.296665869"
        assert (
            menuai.states.get("sensor.energy_consumption_peak_today").state == "unknown"
        )
        assert (
            menuai.states.get("sensor.energy_consumption_off_peak_today").state
            == "unknown"
        )
        assert menuai.states.get("sensor.energy_production_peak_today").state == "unknown"
        assert (
            menuai.states.get("sensor.energy_production_off_peak_today").state
            == "unknown"
        )
        assert menuai.states.get("sensor.gas_today").state == "unknown"

        # Assert mocks are called
        assert len(mock_authenticate.mock_calls) == 1
        assert len(mock_is_authenticated.mock_calls) == 1
        assert len(mock_current_measurements.mock_calls) == 1
