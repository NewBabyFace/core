"""MenuAI SkyConnect firmware update entity."""

from __future__ import annotations

import logging

import aiohttp

from menuai.components.menuai_hardware.coordinator import (
    FirmwareUpdateCoordinator,
)
from menuai.components.menuai_hardware.update import (
    BaseFirmwareUpdateEntity,
    FirmwareUpdateEntityDescription,
)
from menuai.components.menuai_hardware.util import (
    ApplicationType,
    FirmwareInfo,
)
from menuai.components.update import UpdateDeviceClass
from menuai.config_entries import ConfigEntry
from menuai.const import EntityCategory
from menuai.core import menuai, callback
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.device_registry import DeviceInfo
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DOMAIN,
    FIRMWARE,
    FIRMWARE_VERSION,
    NABU_CASA_FIRMWARE_RELEASES_URL,
    PRODUCT,
    SERIAL_NUMBER,
    HardwareVariant,
)

_LOGGER = logging.getLogger(__name__)


FIRMWARE_ENTITY_DESCRIPTIONS: dict[
    ApplicationType | None, FirmwareUpdateEntityDescription
] = {
    ApplicationType.EZSP: FirmwareUpdateEntityDescription(
        key="firmware",
        display_precision=0,
        device_class=UpdateDeviceClass.FIRMWARE,
        entity_category=EntityCategory.CONFIG,
        version_parser=lambda fw: fw.split(" ", 1)[0],
        fw_type="skyconnect_zigbee_ncp",
        version_key="ezsp_version",
        expected_firmware_type=ApplicationType.EZSP,
        firmware_name="EmberZNet Zigbee",
    ),
    ApplicationType.SPINEL: FirmwareUpdateEntityDescription(
        key="firmware",
        display_precision=0,
        device_class=UpdateDeviceClass.FIRMWARE,
        entity_category=EntityCategory.CONFIG,
        version_parser=lambda fw: fw.split("/", 1)[1].split("_", 1)[0],
        fw_type="skyconnect_openthread_rcp",
        version_key="ot_rcp_version",
        expected_firmware_type=ApplicationType.SPINEL,
        firmware_name="OpenThread RCP",
    ),
    ApplicationType.CPC: FirmwareUpdateEntityDescription(
        key="firmware",
        display_precision=0,
        device_class=UpdateDeviceClass.FIRMWARE,
        entity_category=EntityCategory.CONFIG,
        version_parser=lambda fw: fw,
        fw_type="skyconnect_multipan",
        version_key="cpc_version",
        expected_firmware_type=ApplicationType.CPC,
        firmware_name="Multiprotocol",
    ),
    ApplicationType.GECKO_BOOTLOADER: FirmwareUpdateEntityDescription(
        key="firmware",
        display_precision=0,
        device_class=UpdateDeviceClass.FIRMWARE,
        entity_category=EntityCategory.CONFIG,
        version_parser=lambda fw: fw,
        fw_type=None,  # We don't want to update the bootloader
        version_key="gecko_bootloader_version",
        expected_firmware_type=ApplicationType.GECKO_BOOTLOADER,
        firmware_name="Gecko Bootloader",
    ),
    None: FirmwareUpdateEntityDescription(
        key="firmware",
        display_precision=0,
        device_class=UpdateDeviceClass.FIRMWARE,
        entity_category=EntityCategory.CONFIG,
        version_parser=lambda fw: fw,
        fw_type=None,
        version_key=None,
        expected_firmware_type=None,
        firmware_name=None,
    ),
}


def _async_create_update_entity(
    menuai: menuai,
    config_entry: ConfigEntry,
    session: aiohttp.ClientSession,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> FirmwareUpdateEntity:
    """Create an update entity that handles firmware type changes."""
    firmware_type = config_entry.data[FIRMWARE]

    try:
        entity_description = FIRMWARE_ENTITY_DESCRIPTIONS[
            ApplicationType(firmware_type)
        ]
    except (KeyError, ValueError):
        _LOGGER.debug(
            "Unknown firmware type %r, using default entity description", firmware_type
        )
        entity_description = FIRMWARE_ENTITY_DESCRIPTIONS[None]

    entity = FirmwareUpdateEntity(
        device=config_entry.data["device"],
        config_entry=config_entry,
        update_coordinator=FirmwareUpdateCoordinator(
            menuai,
            session,
            NABU_CASA_FIRMWARE_RELEASES_URL,
        ),
        entity_description=entity_description,
    )

    def firmware_type_changed(
        old_type: ApplicationType | None, new_type: ApplicationType | None
    ) -> None:
        """Replace the current entity when the firmware type changes."""
        er.async_get(menuai).async_remove(entity.entity_id)
        async_add_entities(
            [
                _async_create_update_entity(
                    menuai, config_entry, session, async_add_entities
                )
            ]
        )

    entity.async_on_remove(
        entity.add_firmware_type_changed_callback(firmware_type_changed)
    )

    return entity


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the firmware update config entry."""
    session = async_get_clientsession(menuai)
    entity = _async_create_update_entity(
        menuai, config_entry, session, async_add_entities
    )

    async_add_entities([entity])


class FirmwareUpdateEntity(BaseFirmwareUpdateEntity):
    """SkyConnect firmware update entity."""

    bootloader_reset_type = None

    def __init__(
        self,
        device: str,
        config_entry: ConfigEntry,
        update_coordinator: FirmwareUpdateCoordinator,
        entity_description: FirmwareUpdateEntityDescription,
    ) -> None:
        """Initialize the SkyConnect firmware update entity."""
        super().__init__(device, config_entry, update_coordinator, entity_description)

        variant = HardwareVariant.from_usb_product_name(
            self._config_entry.data[PRODUCT]
        )
        serial_number = self._config_entry.data[SERIAL_NUMBER]

        self._attr_unique_id = f"{serial_number}_{self.entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial_number)},
            name=f"{variant.full_name} ({serial_number[:8]})",
            model=variant.full_name,
            manufacturer="Nabu Casa",
            serial_number=serial_number,
        )

        # Use the cached firmware info if it exists
        if self._config_entry.data[FIRMWARE] is not None:
            self._current_firmware_info = FirmwareInfo(
                device=device,
                firmware_type=ApplicationType(self._config_entry.data[FIRMWARE]),
                firmware_version=self._config_entry.data[FIRMWARE_VERSION],
                owners=[],
                source="menuai_sky_connect",
            )

    def _update_attributes(self) -> None:
        """Recompute the attributes of the entity."""
        super()._update_attributes()

        assert self.device_entry is not None
        device_registry = dr.async_get(self.menuai)
        device_registry.async_update_device(
            device_id=self.device_entry.id,
            sw_version=f"{self.entity_description.firmware_name} {self._attr_installed_version}",
        )

    @callback
    def _firmware_info_callback(self, firmware_info: FirmwareInfo) -> None:
        """Handle updated firmware info being pushed by an integration."""
        self.menuai.config_entries.async_update_entry(
            self._config_entry,
            data={
                **self._config_entry.data,
                FIRMWARE: firmware_info.firmware_type,
                FIRMWARE_VERSION: firmware_info.firmware_version,
            },
        )
        super()._firmware_info_callback(firmware_info)
