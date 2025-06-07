"""The Hardware integration."""

from __future__ import annotations

import psutil_home_assistant as ha_psutil

from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from . import websocket_api
from .const import DATA_HARDWARE, DOMAIN
from .hardware import async_process_hardware_platforms
from .models import HardwareData, SystemStatus

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Hardware."""
    menuai.data[DATA_HARDWARE] = HardwareData(
        hardware_platform={},
        system_status=SystemStatus(
            ha_psutil=await menuai.async_add_executor_job(ha_psutil.PsutilWrapper),
            remove_periodic_timer=None,
            subscribers=set(),
        ),
    )
    await async_process_hardware_platforms(menuai)

    await websocket_api.async_setup(menuai)

    return True
