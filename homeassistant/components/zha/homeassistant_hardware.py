"""MenuAI Hardware firmware utilities."""

from __future__ import annotations

from menuai.components.menuai_hardware.util import (
    ApplicationType,
    FirmwareInfo,
    OwningIntegration,
)
from menuai.config_entries import ConfigEntry
from menuai.core import menuai, callback

from .const import DOMAIN
from .helpers import get_zha_gateway


@callback
def get_firmware_info(
    menuai: menuai, config_entry: ConfigEntry
) -> FirmwareInfo | None:
    """Return firmware information for the ZHA instance, synchronously."""

    # We only support EZSP firmware for now
    if config_entry.data.get("radio_type", None) != "ezsp":
        return None

    if (device := config_entry.data.get("device", {}).get("path")) is None:
        return None

    try:
        gateway = get_zha_gateway(menuai)
    except ValueError:
        firmware_version = None
    else:
        firmware_version = gateway.state.node_info.version

    return FirmwareInfo(
        device=device,
        firmware_type=ApplicationType.EZSP,
        firmware_version=firmware_version,
        source=DOMAIN,
        owners=[OwningIntegration(config_entry_id=config_entry.entry_id)],
    )
