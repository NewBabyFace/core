"""The foscam coordinator object."""

import asyncio
from datetime import timedelta
from typing import Any

from libpyfoscam import FoscamCamera

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LOGGER

type FoscamConfigEntry = ConfigEntry[FoscamCoordinator]


class FoscamCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Foscam coordinator."""

    def __init__(
        self,
        menuai: menuai,
        entry: FoscamConfigEntry,
        session: FoscamCamera,
    ) -> None:
        """Initialize my coordinator."""
        super().__init__(
            menuai,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.session = session

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""

        async with asyncio.timeout(30):
            data = {}
            ret, dev_info = await self.menuai.async_add_executor_job(
                self.session.get_dev_info
            )
            if ret == 0:
                data["dev_info"] = dev_info

            all_info = await self.menuai.async_add_executor_job(
                self.session.get_product_all_info
            )
            data["product_info"] = all_info[1]

            ret, is_asleep = await self.menuai.async_add_executor_job(
                self.session.is_asleep
            )
            data["is_asleep"] = {"supported": ret == 0, "status": is_asleep}
            return data
