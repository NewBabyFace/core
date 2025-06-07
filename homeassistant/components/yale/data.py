"""Support for Yale devices."""

from __future__ import annotations

from yalexs.lock import LockDetail
from yalexs.manager.data import YaleXSData
from yalexs_ble import YaleXSBLEDiscovery

from menuai.config_entries import SOURCE_INTEGRATION_DISCOVERY
from menuai.core import menuai, callback
from menuai.exceptions import menuaiError
from menuai.helpers import discovery_flow

from .gateway import YaleGateway

YALEXS_BLE_DOMAIN = "yalexs_ble"


@callback
def _async_trigger_ble_lock_discovery(
    menuai: menuai, locks_with_offline_keys: list[LockDetail]
) -> None:
    """Update keys for the yalexs-ble integration if available."""
    for lock_detail in locks_with_offline_keys:
        discovery_flow.async_create_flow(
            menuai,
            YALEXS_BLE_DOMAIN,
            context={"source": SOURCE_INTEGRATION_DISCOVERY},
            data=YaleXSBLEDiscovery(
                {
                    "name": lock_detail.device_name,
                    "address": lock_detail.mac_address,
                    "serial": lock_detail.serial_number,
                    "key": lock_detail.offline_key,
                    "slot": lock_detail.offline_slot,
                }
            ),
        )


class YaleData(YaleXSData):
    """yale data object."""

    def __init__(self, menuai: menuai, yale_gateway: YaleGateway) -> None:
        """Init yale data object."""
        self._menuai = menuai
        super().__init__(yale_gateway, menuaiError)

    @callback
    def async_offline_key_discovered(self, detail: LockDetail) -> None:
        """Handle offline key discovery."""
        _async_trigger_ble_lock_discovery(self._menuai, [detail])
