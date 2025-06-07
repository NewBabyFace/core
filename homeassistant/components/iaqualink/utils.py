"""Utility functions for Aqualink devices."""

from __future__ import annotations

from collections.abc import Awaitable

import httpx
from iaqualink.exception import AqualinkServiceException

from menuai.exceptions import menuaiError


async def await_or_reraise(awaitable: Awaitable) -> None:
    """Execute API call while catching service exceptions."""
    try:
        await awaitable
    except (AqualinkServiceException, httpx.HTTPError) as svc_exception:
        raise menuaiError(f"Aqualink error: {svc_exception}") from svc_exception
