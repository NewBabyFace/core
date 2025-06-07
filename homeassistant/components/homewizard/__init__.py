"""The Homewizard integration."""

from homewizard_energy import (
    HomeWizardEnergy,
    HomeWizardEnergyV1,
    HomeWizardEnergyV2,
    has_v2_api,
)

from menuai.config_entries import SOURCE_REAUTH
from menuai.const import CONF_IP_ADDRESS, CONF_TOKEN
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.issue_registry import IssueSeverity, async_create_issue

from .const import DOMAIN, PLATFORMS
from .coordinator import HomeWizardConfigEntry, HWEnergyDeviceUpdateCoordinator


async def async_setup_entry(menuai: menuai, entry: HomeWizardConfigEntry) -> bool:
    """Set up Homewizard from a config entry."""

    api: HomeWizardEnergy

    is_battery = entry.unique_id.startswith("HWE-BAT") if entry.unique_id else False

    if (token := entry.data.get(CONF_TOKEN)) and is_battery:
        api = HomeWizardEnergyV2(
            entry.data[CONF_IP_ADDRESS],
            token=token,
            clientsession=async_get_clientsession(menuai),
        )
    else:
        api = HomeWizardEnergyV1(
            entry.data[CONF_IP_ADDRESS],
            clientsession=async_get_clientsession(menuai),
        )

        if is_battery:
            await async_check_v2_support_and_create_issue(menuai, entry)

    coordinator = HWEnergyDeviceUpdateCoordinator(menuai, entry, api)
    try:
        await coordinator.async_config_entry_first_refresh()

    except ConfigEntryNotReady:
        await coordinator.api.close()

        if coordinator.api_disabled:
            entry.async_start_reauth(menuai)

        raise

    entry.runtime_data = coordinator

    # Abort reauth config flow if active
    for progress_flow in menuai.config_entries.flow.async_progress_by_handler(DOMAIN):
        if (
            "context" in progress_flow
            and progress_flow["context"].get("source") == SOURCE_REAUTH
        ):
            menuai.config_entries.flow.async_abort(progress_flow["flow_id"])

    # Finalize
    entry.async_on_unload(coordinator.api.close)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: HomeWizardConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_check_v2_support_and_create_issue(
    menuai: menuai, entry: HomeWizardConfigEntry
) -> None:
    """Check if the device supports v2 and create an issue if not."""

    if not await has_v2_api(entry.data[CONF_IP_ADDRESS], async_get_clientsession(menuai)):
        return

    async_create_issue(
        menuai,
        DOMAIN,
        f"migrate_to_v2_api_{entry.entry_id}",
        is_fixable=True,
        is_persistent=False,
        learn_more_url="https://home-assistant.io/integrations/homewizard/#which-button-do-i-need-to-press-to-configure-the-device",
        translation_key="migrate_to_v2_api",
        translation_placeholders={
            "title": entry.title,
        },
        severity=IssueSeverity.WARNING,
        data={"entry_id": entry.entry_id},
    )
