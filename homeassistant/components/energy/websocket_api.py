"""The Energy websocket API."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import timedelta
import functools
from itertools import chain
from typing import Any, cast

import voluptuous as vol

from menuai.components import recorder, websocket_api
from menuai.components.recorder.statistics import StatisticsRow
from menuai.const import UnitOfEnergy
from menuai.core import menuai, callback
from menuai.helpers.integration_platform import (
    async_process_integration_platforms,
)
from menuai.helpers.singleton import singleton
from menuai.util import dt as dt_util

from .const import DOMAIN
from .data import (
    DEVICE_CONSUMPTION_SCHEMA,
    ENERGY_SOURCE_SCHEMA,
    EnergyManager,
    EnergyPreferencesUpdate,
    async_get_manager,
)
from .types import EnergyPlatform, GetSolarForecastType, SolarForecastType
from .validate import async_validate

type EnergyWebSocketCommandHandler = Callable[
    [menuai, websocket_api.ActiveConnection, dict[str, Any], EnergyManager],
    None,
]
type AsyncEnergyWebSocketCommandHandler = Callable[
    [menuai, websocket_api.ActiveConnection, dict[str, Any], EnergyManager],
    Coroutine[Any, Any, None],
]


@callback
def async_setup(menuai: menuai) -> None:
    """Set up the energy websocket API."""
    websocket_api.async_register_command(menuai, ws_get_prefs)
    websocket_api.async_register_command(menuai, ws_save_prefs)
    websocket_api.async_register_command(menuai, ws_info)
    websocket_api.async_register_command(menuai, ws_validate)
    websocket_api.async_register_command(menuai, ws_solar_forecast)
    websocket_api.async_register_command(menuai, ws_get_fossil_energy_consumption)


@singleton("energy_platforms")
async def async_get_energy_platforms(
    menuai: menuai,
) -> dict[str, GetSolarForecastType]:
    """Get energy platforms."""
    platforms: dict[str, GetSolarForecastType] = {}

    @callback
    def _process_energy_platform(
        menuai: menuai,
        domain: str,
        platform: EnergyPlatform,
    ) -> None:
        """Process energy platforms."""
        if not hasattr(platform, "async_get_solar_forecast"):
            return

        platforms[domain] = platform.async_get_solar_forecast

    await async_process_integration_platforms(
        menuai, DOMAIN, _process_energy_platform, wait_for_platforms=True
    )

    return platforms


def _ws_with_manager(
    func: AsyncEnergyWebSocketCommandHandler | EnergyWebSocketCommandHandler,
) -> websocket_api.AsyncWebSocketCommandHandler:
    """Decorate a function to pass in a manager."""

    @functools.wraps(func)
    async def with_manager(
        menuai: menuai,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        manager = await async_get_manager(menuai)

        result = func(menuai, connection, msg, manager)

        if asyncio.iscoroutine(result):
            await result

    return with_manager


@websocket_api.websocket_command(
    {
        vol.Required("type"): "energy/get_prefs",
    }
)
@websocket_api.async_response
@_ws_with_manager
@callback
def ws_get_prefs(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: EnergyManager,
) -> None:
    """Handle get prefs command."""
    if manager.data is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "No prefs")
        return

    connection.send_result(msg["id"], manager.data)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "energy/save_prefs",
        vol.Optional("energy_sources"): ENERGY_SOURCE_SCHEMA,
        vol.Optional("device_consumption"): [DEVICE_CONSUMPTION_SCHEMA],
    }
)
@websocket_api.async_response
@_ws_with_manager
async def ws_save_prefs(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: EnergyManager,
) -> None:
    """Handle get prefs command."""
    msg_id = msg.pop("id")
    msg.pop("type")
    await manager.async_update(cast(EnergyPreferencesUpdate, msg))
    connection.send_result(msg_id, manager.data)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "energy/info",
    }
)
@websocket_api.async_response
async def ws_info(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle get info command."""
    forecast_platforms = await async_get_energy_platforms(menuai)
    connection.send_result(
        msg["id"],
        {
            "cost_sensors": menuai.data[DOMAIN]["cost_sensors"],
            "solar_forecast_domains": list(forecast_platforms),
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "energy/validate",
    }
)
@websocket_api.async_response
async def ws_validate(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle validate command."""
    connection.send_result(msg["id"], (await async_validate(menuai)).as_dict())


@websocket_api.websocket_command(
    {
        vol.Required("type"): "energy/solar_forecast",
    }
)
@websocket_api.async_response
@_ws_with_manager
async def ws_solar_forecast(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: EnergyManager,
) -> None:
    """Handle solar forecast command."""
    if manager.data is None:
        connection.send_result(msg["id"], {})
        return

    config_entries: dict[str, str | None] = {}

    for source in manager.data["energy_sources"]:
        if (
            source["type"] != "solar"
            or (solar_forecast := source.get("config_entry_solar_forecast")) is None
        ):
            continue

        for entry in solar_forecast:
            config_entries[entry] = None

    if not config_entries:
        connection.send_result(msg["id"], {})
        return

    forecasts: dict[str, SolarForecastType] = {}

    forecast_platforms = await async_get_energy_platforms(menuai)

    for config_entry_id in config_entries:
        config_entry = menuai.config_entries.async_get_entry(config_entry_id)
        # Filter out non-existing config entries or unsupported domains

        if config_entry is None or config_entry.domain not in forecast_platforms:
            continue

        forecast = await forecast_platforms[config_entry.domain](menuai, config_entry_id)

        if forecast is not None:
            forecasts[config_entry_id] = forecast

    connection.send_result(msg["id"], forecasts)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "energy/fossil_energy_consumption",
        vol.Required("start_time"): str,
        vol.Required("end_time"): str,
        vol.Required("energy_statistic_ids"): [str],
        vol.Required("co2_statistic_id"): str,
        vol.Required("period"): vol.Any("5minute", "hour", "day", "month"),
    }
)
@websocket_api.async_response
async def ws_get_fossil_energy_consumption(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Calculate amount of fossil based energy."""
    start_time_str = msg["start_time"]
    end_time_str = msg["end_time"]

    if start_time := dt_util.parse_datetime(start_time_str):
        start_time = dt_util.as_utc(start_time)
    else:
        connection.send_error(msg["id"], "invalid_start_time", "Invalid start_time")
        return

    if end_time := dt_util.parse_datetime(end_time_str):
        end_time = dt_util.as_utc(end_time)
    else:
        connection.send_error(msg["id"], "invalid_end_time", "Invalid end_time")
        return

    statistic_ids = set(msg["energy_statistic_ids"])
    statistic_ids.add(msg["co2_statistic_id"])

    # Fetch energy + CO2 statistics
    statistics = await recorder.get_instance(menuai).async_add_executor_job(
        recorder.statistics.statistics_during_period,
        menuai,
        start_time,
        end_time,
        statistic_ids,
        "hour",
        {"energy": UnitOfEnergy.KILO_WATT_HOUR},
        {"mean", "change"},
    )

    def _combine_change_statistics(
        stats: dict[str, list[StatisticsRow]], statistic_ids: list[str]
    ) -> dict[float, float]:
        """Combine multiple statistics, returns a dict indexed by start time."""
        result: defaultdict[float, float] = defaultdict(float)

        for statistics_id, stat in stats.items():
            if statistics_id not in statistic_ids:
                continue
            for period in stat:
                if (change := period.get("change")) is None:
                    continue
                result[period["start"]] += change

        return {key: result[key] for key in sorted(result)}

    def _reduce_deltas(
        stat_list: list[dict[str, Any]],
        same_period: Callable[[float, float], bool],
        period_start_end: Callable[[float], tuple[float, float]],
        period: timedelta,
    ) -> list[dict[str, Any]]:
        """Reduce hourly deltas to daily or monthly deltas."""
        result: list[dict[str, Any]] = []
        deltas: list[float] = []
        if not stat_list:
            return result
        prev_stat: dict[str, Any] = stat_list[0]
        fake_stat = {"start": stat_list[-1]["start"] + period.total_seconds()}

        # Loop over the hourly deltas + a fake entry to end the period
        for statistic in chain(stat_list, (fake_stat,)):
            if not same_period(prev_stat["start"], statistic["start"]):
                start, _ = period_start_end(prev_stat["start"])
                # The previous statistic was the last entry of the period
                result.append(
                    {
                        "start": dt_util.utc_from_timestamp(start).isoformat(),
                        "delta": sum(deltas),
                    }
                )
                deltas = []
            if statistic.get("delta") is not None:
                deltas.append(statistic["delta"])
            prev_stat = statistic

        return result

    merged_energy_statistics = _combine_change_statistics(
        statistics, msg["energy_statistic_ids"]
    )
    indexed_co2_statistics = cast(
        dict[float, float],
        {
            period["start"]: period["mean"]
            for period in statistics.get(msg["co2_statistic_id"], {})
        },
    )

    # Calculate amount of fossil based energy, assume 100% fossil if missing
    fossil_energy = [
        {"start": start, "delta": delta * indexed_co2_statistics.get(start, 100) / 100}
        for start, delta in merged_energy_statistics.items()
    ]

    if msg["period"] == "hour":
        reduced_fossil_energy = [
            {
                "start": dt_util.utc_from_timestamp(period["start"]).isoformat(),
                "delta": period["delta"],
            }
            for period in fossil_energy
        ]

    elif msg["period"] == "day":
        _same_day_ts, _day_start_end_ts = recorder.statistics.reduce_day_ts_factory()
        reduced_fossil_energy = _reduce_deltas(
            fossil_energy,
            _same_day_ts,
            _day_start_end_ts,
            timedelta(days=1),
        )
    else:
        (
            _same_month_ts,
            _month_start_end_ts,
        ) = recorder.statistics.reduce_month_ts_factory()
        reduced_fossil_energy = _reduce_deltas(
            fossil_energy,
            _same_month_ts,
            _month_start_end_ts,
            timedelta(days=1),
        )

    result = {period["start"]: period["delta"] for period in reduced_fossil_energy}
    connection.send_result(msg["id"], result)
