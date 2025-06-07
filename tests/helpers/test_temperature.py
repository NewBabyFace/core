"""Tests MenuAI temperature helpers."""

import pytest

from menuai.const import (
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    UnitOfTemperature,
)
from menuai.core import menuai
from menuai.helpers.temperature import display_temp

TEMP = 24.636626


def test_temperature_not_a_number(menuai: menuai) -> None:
    """Test that temperature is a number."""
    temp = "Temperature"
    with pytest.raises(Exception) as exception:
        display_temp(menuai, temp, UnitOfTemperature.CELSIUS, PRECISION_HALVES)

    assert f"Temperature is not a number: {temp}" in str(exception.value)


def test_celsius_halves(menuai: menuai) -> None:
    """Test temperature to celsius rounding to halves."""
    assert display_temp(menuai, TEMP, UnitOfTemperature.CELSIUS, PRECISION_HALVES) == 24.5


def test_celsius_tenths(menuai: menuai) -> None:
    """Test temperature to celsius rounding to tenths."""
    assert display_temp(menuai, TEMP, UnitOfTemperature.CELSIUS, PRECISION_TENTHS) == 24.6


def test_fahrenheit_wholes(menuai: menuai) -> None:
    """Test temperature to fahrenheit rounding to wholes."""
    assert display_temp(menuai, TEMP, UnitOfTemperature.FAHRENHEIT, PRECISION_WHOLE) == -4
