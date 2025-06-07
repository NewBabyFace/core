"""Support for Ecovacs Deebot vacuums."""

from sucks import VacBot

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

from .controller import EcovacsController

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.IMAGE,
    Platform.LAWN_MOWER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VACUUM,
]
type EcovacsConfigEntry = ConfigEntry[EcovacsController]


async def async_setup_entry(menuai: menuai, entry: EcovacsConfigEntry) -> bool:
    """Set up this integration using UI."""
    controller = EcovacsController(menuai, entry.data)
    await controller.initialize()

    async def on_unload() -> None:
        await controller.teardown()

    entry.async_on_unload(on_unload)
    entry.runtime_data = controller

    async def _async_wait_connect(device: VacBot) -> None:
        await menuai.async_add_executor_job(device.connect_and_wait_until_ready)

    for device in controller.legacy_devices:
        entry.async_create_background_task(
            menuai=menuai,
            target=_async_wait_connect(device),
            name=f"{entry.title}_wait_connect_{device.vacuum['did']}",
        )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: EcovacsConfigEntry) -> bool:
    """Unload config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
