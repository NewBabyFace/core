"""Helpers for Waze Travel Time integration."""

import logging

from pywaze.route_calculator import WazeRouteCalculator, WRCError

from menuai.core import menuai
from menuai.helpers.httpx_client import get_async_client
from menuai.helpers.location import find_coordinates

_LOGGER = logging.getLogger(__name__)


async def is_valid_config_entry(
    menuai: menuai, origin: str, destination: str, region: str
) -> bool:
    """Return whether the config entry data is valid."""
    resolved_origin = find_coordinates(menuai, origin)
    resolved_destination = find_coordinates(menuai, destination)
    httpx_client = get_async_client(menuai)
    client = WazeRouteCalculator(region=region, client=httpx_client)
    try:
        await client.calc_routes(resolved_origin, resolved_destination)
    except WRCError as error:
        _LOGGER.error("Error trying to validate entry: %s", error)
        return False
    return True
