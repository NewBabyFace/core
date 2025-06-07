"""Helpers for LaMetric."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, Concatenate

from demetriek import LaMetricConnectionError, LaMetricError

from menuai.core import menuai, callback
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import LaMetricDataUpdateCoordinator
from .entity import LaMetricEntity


def lametric_exception_handler[_LaMetricEntityT: LaMetricEntity, **_P](
    func: Callable[Concatenate[_LaMetricEntityT, _P], Coroutine[Any, Any, Any]],
) -> Callable[Concatenate[_LaMetricEntityT, _P], Coroutine[Any, Any, None]]:
    """Decorate LaMetric calls to handle LaMetric exceptions.

    A decorator that wraps the passed in function, catches LaMetric errors,
    and handles the availability of the device in the data coordinator.
    """

    async def handler(
        self: _LaMetricEntityT, *args: _P.args, **kwargs: _P.kwargs
    ) -> None:
        try:
            await func(self, *args, **kwargs)
            self.coordinator.async_update_listeners()

        except LaMetricConnectionError as error:
            self.coordinator.last_update_success = False
            self.coordinator.async_update_listeners()
            raise menuaiError(
                "Error communicating with the LaMetric device"
            ) from error

        except LaMetricError as error:
            raise menuaiError(
                "Invalid response from the LaMetric device"
            ) from error

    return handler


@callback
def async_get_coordinator_by_device_id(
    menuai: menuai, device_id: str
) -> LaMetricDataUpdateCoordinator:
    """Get the LaMetric coordinator for this device ID."""
    device_registry = dr.async_get(menuai)

    if (device_entry := device_registry.async_get(device_id)) is None:
        raise ValueError(f"Unknown LaMetric device ID: {device_id}")

    for entry_id in device_entry.config_entries:
        if (
            (entry := menuai.config_entries.async_get_entry(entry_id))
            and entry.domain == DOMAIN
            and entry.entry_id in menuai.data[DOMAIN]
        ):
            coordinator: LaMetricDataUpdateCoordinator = menuai.data[DOMAIN][
                entry.entry_id
            ]
            return coordinator

    raise ValueError(f"No coordinator for device ID: {device_id}")
