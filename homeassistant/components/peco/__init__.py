"""The PECO Outage Counter integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from peco import (
    AlertResults,
    BadJSONError,
    HttpError,
    OutageResults,
    PecoOutageApi,
    UnresponsiveMeterError,
)

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_COUNTY,
    CONF_PHONE_NUMBER,
    DOMAIN,
    LOGGER,
    OUTAGE_SCAN_INTERVAL,
    SMART_METER_SCAN_INTERVAL,
)

PLATFORMS: Final = [Platform.BINARY_SENSOR, Platform.SENSOR]


@dataclass
class PECOCoordinatorData:
    """Something to hold the data for PECO."""

    outages: OutageResults
    alerts: AlertResults


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up PECO Outage Counter from a config entry."""

    websession = async_get_clientsession(menuai)
    api = PecoOutageApi()
    # Outage Counter Setup
    county: str = entry.data[CONF_COUNTY]

    async def async_update_outage_data() -> PECOCoordinatorData:
        """Fetch data from API."""
        try:
            outages: OutageResults = (
                await api.get_outage_totals(websession)
                if county == "TOTAL"
                else await api.get_outage_count(county, websession)
            )
            alerts: AlertResults = await api.get_map_alerts(websession)
            data = PECOCoordinatorData(outages, alerts)
        except HttpError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
        except BadJSONError as err:
            raise UpdateFailed(f"Error parsing data: {err}") from err
        return data

    outage_coordinator = DataUpdateCoordinator(
        menuai,
        LOGGER,
        config_entry=entry,
        name="PECO Outage Count",
        update_method=async_update_outage_data,
        update_interval=timedelta(minutes=OUTAGE_SCAN_INTERVAL),
    )

    await outage_coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "outage_count": outage_coordinator
    }

    if phone_number := entry.data.get(CONF_PHONE_NUMBER):
        # Smart Meter Setup]

        async def async_update_meter_data() -> bool:
            """Fetch data from API."""
            try:
                data: bool = await api.meter_check(phone_number, websession)
            except UnresponsiveMeterError as err:
                raise UpdateFailed("Unresponsive meter") from err
            except HttpError as err:
                raise UpdateFailed(f"Error fetching data: {err}") from err
            except BadJSONError as err:
                raise UpdateFailed(f"Error parsing data: {err}") from err
            return data

        meter_coordinator = DataUpdateCoordinator(
            menuai,
            LOGGER,
            config_entry=entry,
            name="PECO Smart Meter",
            update_method=async_update_meter_data,
            update_interval=timedelta(minutes=SMART_METER_SCAN_INTERVAL),
        )

        await meter_coordinator.async_config_entry_first_refresh()

        menuai.data[DOMAIN][entry.entry_id]["smart_meter"] = meter_coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
