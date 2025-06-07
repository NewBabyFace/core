"""The Goodwe inverter component."""

from goodwe import InverterError, connect

from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.device_registry import DeviceInfo

from .const import CONF_MODEL_FAMILY, DOMAIN, PLATFORMS
from .coordinator import GoodweConfigEntry, GoodweRuntimeData, GoodweUpdateCoordinator


async def async_setup_entry(menuai: menuai, entry: GoodweConfigEntry) -> bool:
    """Set up the Goodwe components from a config entry."""
    host = entry.data[CONF_HOST]
    model_family = entry.data[CONF_MODEL_FAMILY]

    # Connect to Goodwe inverter
    try:
        inverter = await connect(
            host=host,
            family=model_family,
            retries=10,
        )
    except InverterError as err:
        raise ConfigEntryNotReady from err

    device_info = DeviceInfo(
        configuration_url="https://www.semsportal.com",
        identifiers={(DOMAIN, inverter.serial_number)},
        name=entry.title,
        manufacturer="GoodWe",
        model=inverter.model_name,
        sw_version=f"{inverter.firmware} / {inverter.arm_firmware}",
    )

    # Create update coordinator
    coordinator = GoodweUpdateCoordinator(menuai, entry, inverter)

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = GoodweRuntimeData(
        inverter=inverter,
        coordinator=coordinator,
        device_info=device_info,
    )

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, config_entry: GoodweConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def update_listener(menuai: menuai, config_entry: GoodweConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(config_entry.entry_id)
