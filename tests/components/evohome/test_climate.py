"""The tests for the climate platform of evohome.

All evohome systems have controllers and at least one zone.
"""

from __future__ import annotations

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .conftest import setup_evohome
from .const import TEST_INSTALLS


@pytest.mark.parametrize("install", [*TEST_INSTALLS, "botched"])
async def test_setup_platform(
    menuai: menuai,
    config: dict[str, str],
    install: str,
    snapshot: SnapshotAssertion,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test entities and their states after setup of evohome."""

    # Cannot use the evohome fixture, as need to set dtm first
    #  - some extended state attrs are relative the current time
    freezer.move_to("2024-07-10T12:00:00Z")

    async for _ in setup_evohome(menuai, config, install=install):
        pass

    for x in menuai.states.async_all(Platform.CLIMATE):
        assert x == snapshot(name=f"{x.entity_id}-state")


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_ctl_set_hvac_mode(
    menuai: menuai,
    ctl_id: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test SERVICE_SET_HVAC_MODE of an evohome controller."""

    results = []

    # SERVICE_SET_HVAC_MODE: HVACMode.OFF
    with patch("evohomeasync2.control_system.ControlSystem.set_mode") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: ctl_id,
                ATTR_HVAC_MODE: HVACMode.OFF,
            },
            blocking=True,
        )

        try:
            mock_fcn.assert_awaited_once_with("HeatingOff", until=None)
        except AssertionError:
            mock_fcn.assert_awaited_once_with("Off", until=None)

        results.append(mock_fcn.await_args.args)  # type: ignore[union-attr]

    # SERVICE_SET_HVAC_MODE: HVACMode.HEAT
    with patch("evohomeasync2.control_system.ControlSystem.set_mode") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: ctl_id,
                ATTR_HVAC_MODE: HVACMode.HEAT,
            },
            blocking=True,
        )

        try:
            mock_fcn.assert_awaited_once_with("Auto", until=None)
        except AssertionError:
            mock_fcn.assert_awaited_once_with("Heat", until=None)

        results.append(mock_fcn.await_args.args)  # type: ignore[union-attr]

    assert results == snapshot


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_ctl_set_temperature(
    menuai: menuai,
    ctl_id: str,
) -> None:
    """Test SERVICE_SET_TEMPERATURE of an evohome controller."""

    # Entity climate.xxx does not support this service
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: ctl_id,
                ATTR_TEMPERATURE: 19.1,
            },
            blocking=True,
        )


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_ctl_turn_off(
    menuai: menuai,
    ctl_id: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test SERVICE_TURN_OFF of an evohome controller."""

    results = []

    # SERVICE_TURN_OFF
    with patch("evohomeasync2.control_system.ControlSystem.set_mode") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: ctl_id,
            },
            blocking=True,
        )

        try:
            mock_fcn.assert_awaited_once_with("HeatingOff", until=None)
        except AssertionError:
            mock_fcn.assert_awaited_once_with("Off", until=None)

        results.append(mock_fcn.await_args.args)  # type: ignore[union-attr]

    assert results == snapshot


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_ctl_turn_on(
    menuai: menuai,
    ctl_id: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test SERVICE_TURN_ON of an evohome controller."""

    results = []

    # SERVICE_TURN_ON
    with patch("evohomeasync2.control_system.ControlSystem.set_mode") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: ctl_id,
            },
            blocking=True,
        )

        try:
            mock_fcn.assert_awaited_once_with("Auto", until=None)
        except AssertionError:
            mock_fcn.assert_awaited_once_with("Heat", until=None)

        results.append(mock_fcn.await_args.args)  # type: ignore[union-attr]

    assert results == snapshot


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_zone_set_hvac_mode(
    menuai: menuai,
    zone_id: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test SERVICE_SET_HVAC_MODE of an evohome heating zone."""

    results = []

    # SERVICE_SET_HVAC_MODE: HVACMode.HEAT
    with patch("evohomeasync2.zone.Zone.reset") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: zone_id,
                ATTR_HVAC_MODE: HVACMode.HEAT,
            },
            blocking=True,
        )

        mock_fcn.assert_awaited_once_with()

    # SERVICE_SET_HVAC_MODE: HVACMode.OFF
    with patch("evohomeasync2.zone.Zone.set_temperature") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: zone_id,
                ATTR_HVAC_MODE: HVACMode.OFF,
            },
            blocking=True,
        )

        mock_fcn.assert_awaited_once()

        assert mock_fcn.await_args is not None  # mypy hint
        assert mock_fcn.await_args.args != ()  # minimum target temp
        assert mock_fcn.await_args.kwargs == {"until": None}

        results.append(mock_fcn.await_args.args)

    assert results == snapshot


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_zone_set_preset_mode(
    menuai: menuai,
    zone_id: str,
    freezer: FrozenDateTimeFactory,
    snapshot: SnapshotAssertion,
) -> None:
    """Test SERVICE_SET_PRESET_MODE of an evohome heating zone."""

    freezer.move_to("2024-07-10T12:00:00Z")
    results = []

    # SERVICE_SET_PRESET_MODE: none
    with patch("evohomeasync2.zone.Zone.reset") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_SET_PRESET_MODE,
            {
                ATTR_ENTITY_ID: zone_id,
                ATTR_PRESET_MODE: "none",
            },
            blocking=True,
        )

        mock_fcn.assert_awaited_once_with()

    # SERVICE_SET_PRESET_MODE: permanent
    with patch("evohomeasync2.zone.Zone.set_temperature") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_SET_PRESET_MODE,
            {
                ATTR_ENTITY_ID: zone_id,
                ATTR_PRESET_MODE: "permanent",
            },
            blocking=True,
        )

        mock_fcn.assert_awaited_once()

        assert mock_fcn.await_args is not None  # mypy hint
        assert mock_fcn.await_args.args != ()  # current target temp
        assert mock_fcn.await_args.kwargs == {"until": None}

        results.append(mock_fcn.await_args.args)

    # SERVICE_SET_PRESET_MODE: temporary
    with patch("evohomeasync2.zone.Zone.set_temperature") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_SET_PRESET_MODE,
            {
                ATTR_ENTITY_ID: zone_id,
                ATTR_PRESET_MODE: "temporary",
            },
            blocking=True,
        )

        mock_fcn.assert_awaited_once()

        assert mock_fcn.await_args is not None  # mypy hint
        assert mock_fcn.await_args.args != ()  # current target temp
        assert mock_fcn.await_args.kwargs != {}  # next setpoint dtm

        results.append(mock_fcn.await_args.args)
        results.append(mock_fcn.await_args.kwargs)

    assert results == snapshot


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_zone_set_temperature(
    menuai: menuai,
    zone_id: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test SERVICE_SET_TEMPERATURE of an evohome heating zone."""

    results = []

    # SERVICE_SET_TEMPERATURE: temperature
    with patch("evohomeasync2.zone.Zone.set_temperature") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: zone_id,
                ATTR_TEMPERATURE: 19.1,
            },
            blocking=True,
        )

        mock_fcn.assert_awaited_once()

        assert mock_fcn.await_args is not None  # mypy hint
        assert mock_fcn.await_args.args == (19.1,)
        assert mock_fcn.await_args.kwargs != {}  # next setpoint dtm

        results.append(mock_fcn.await_args.kwargs)

    assert results == snapshot


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_zone_turn_off(
    menuai: menuai,
    zone_id: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test SERVICE_TURN_OFF of an evohome heating zone."""

    results = []

    # SERVICE_TURN_OFF
    with patch("evohomeasync2.zone.Zone.set_temperature") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: zone_id,
            },
            blocking=True,
        )

        mock_fcn.assert_awaited_once()

        assert mock_fcn.await_args is not None  # mypy hint
        assert mock_fcn.await_args.args != ()  # minimum target temp
        assert mock_fcn.await_args.kwargs == {"until": None}

        results.append(mock_fcn.await_args.args)

    assert results == snapshot


@pytest.mark.parametrize("install", TEST_INSTALLS)
async def test_zone_turn_on(
    menuai: menuai,
    zone_id: str,
) -> None:
    """Test SERVICE_TURN_ON of an evohome heating zone."""

    # SERVICE_TURN_ON
    with patch("evohomeasync2.zone.Zone.reset") as mock_fcn:
        await menuai.services.async_call(
            Platform.CLIMATE,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: zone_id,
            },
            blocking=True,
        )

        mock_fcn.assert_awaited_once_with()
