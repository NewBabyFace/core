"""The Shelly integration."""

from __future__ import annotations

from typing import Final

from aioshelly.ble.const import BLE_SCRIPT_NAME
from aioshelly.block_device import BlockDevice
from aioshelly.common import ConnectionOptions
from aioshelly.const import DEFAULT_COAP_PORT, RPC_GENERATIONS
from aioshelly.exceptions import (
    DeviceConnectionError,
    InvalidAuthError,
    MacAddressMismatchError,
    RpcCallError,
)
from aioshelly.rpc_device import RpcDevice, bluetooth_mac_from_primary_mac
import voluptuous as vol

from menuai.components.bluetooth import async_remove_scanner
from menuai.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.device_registry import CONNECTION_NETWORK_MAC
from menuai.helpers.typing import ConfigType

from .const import (
    BLOCK_EXPECTED_SLEEP_PERIOD,
    BLOCK_WRONG_SLEEP_PERIOD,
    CONF_COAP_PORT,
    CONF_SLEEP_PERIOD,
    DOMAIN,
    FIRMWARE_UNSUPPORTED_ISSUE_ID,
    LOGGER,
    MODELS_WITH_WRONG_SLEEP_PERIOD,
    PUSH_UPDATE_ISSUE_ID,
)
from .coordinator import (
    ShellyBlockCoordinator,
    ShellyConfigEntry,
    ShellyEntryData,
    ShellyRestCoordinator,
    ShellyRpcCoordinator,
    ShellyRpcPollingCoordinator,
)
from .repairs import async_manage_ble_scanner_firmware_unsupported_issue
from .utils import (
    async_create_issue_unsupported_firmware,
    get_coap_context,
    get_device_entry_gen,
    get_http_port,
    get_rpc_scripts_event_types,
    get_ws_context,
)

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.UPDATE,
    Platform.VALVE,
]
BLOCK_SLEEPING_PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]
RPC_SLEEPING_PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.UPDATE,
]

COAP_SCHEMA: Final = vol.Schema(
    {
        vol.Optional(CONF_COAP_PORT, default=DEFAULT_COAP_PORT): cv.port,
    }
)
CONFIG_SCHEMA: Final = vol.Schema({DOMAIN: COAP_SCHEMA}, extra=vol.ALLOW_EXTRA)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Shelly component."""
    if (conf := config.get(DOMAIN)) is not None:
        menuai.data[DOMAIN] = {CONF_COAP_PORT: conf[CONF_COAP_PORT]}

    return True


async def async_setup_entry(menuai: menuai, entry: ShellyConfigEntry) -> bool:
    """Set up Shelly from a config entry."""
    entry.runtime_data = ShellyEntryData([])

    # The custom component for Shelly devices uses shelly domain as well as core
    # integration. If the user removes the custom component but doesn't remove the
    # config entry, core integration will try to configure that config entry with an
    # error. The config entry data for this custom component doesn't contain host
    # value, so if host isn't present, config entry will not be configured.
    if not entry.data.get(CONF_HOST):
        LOGGER.warning(
            (
                "The config entry %s probably comes from a custom integration, please"
                " remove it if you want to use core Shelly integration"
            ),
            entry.title,
        )
        return False

    if get_device_entry_gen(entry) in RPC_GENERATIONS:
        return await _async_setup_rpc_entry(menuai, entry)

    return await _async_setup_block_entry(menuai, entry)


async def _async_setup_block_entry(
    menuai: menuai, entry: ShellyConfigEntry
) -> bool:
    """Set up Shelly block based device from a config entry."""
    options = ConnectionOptions(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
        device_mac=entry.unique_id,
    )

    coap_context = await get_coap_context(menuai)

    device = await BlockDevice.create(
        async_get_clientsession(menuai),
        coap_context,
        options,
    )

    dev_reg = dr.async_get(menuai)
    device_entry = None
    if entry.unique_id is not None:
        device_entry = dev_reg.async_get_device(
            connections={(CONNECTION_NETWORK_MAC, dr.format_mac(entry.unique_id))},
        )
    # https://github.com/home-assistant/core/pull/48076
    if device_entry and entry.entry_id not in device_entry.config_entries:
        device_entry = None

    sleep_period = entry.data.get(CONF_SLEEP_PERIOD)
    runtime_data = entry.runtime_data
    runtime_data.platforms = BLOCK_SLEEPING_PLATFORMS

    # Some old firmware have a wrong sleep period hardcoded value.
    # Following code block will force the right value for affected devices
    if (
        sleep_period == BLOCK_WRONG_SLEEP_PERIOD
        and entry.data[CONF_MODEL] in MODELS_WITH_WRONG_SLEEP_PERIOD
    ):
        LOGGER.warning(
            "Updating stored sleep period for %s: from %s to %s",
            entry.title,
            sleep_period,
            BLOCK_EXPECTED_SLEEP_PERIOD,
        )
        data = {**entry.data}
        data[CONF_SLEEP_PERIOD] = sleep_period = BLOCK_EXPECTED_SLEEP_PERIOD
        menuai.config_entries.async_update_entry(entry, data=data)

    if sleep_period == 0:
        # Not a sleeping device, finish setup
        LOGGER.debug("Setting up online block device %s", entry.title)
        runtime_data.platforms = PLATFORMS
        try:
            await device.initialize()
            if not device.firmware_supported:
                async_create_issue_unsupported_firmware(menuai, entry)
                await device.shutdown()
                raise ConfigEntryNotReady(
                    translation_domain=DOMAIN,
                    translation_key="firmware_unsupported",
                    translation_placeholders={"device": entry.title},
                )
        except (DeviceConnectionError, MacAddressMismatchError) as err:
            await device.shutdown()
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="device_communication_error",
                translation_placeholders={"device": entry.title},
            ) from err
        except InvalidAuthError as err:
            await device.shutdown()
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_error",
                translation_placeholders={"device": entry.title},
            ) from err

        runtime_data.block = ShellyBlockCoordinator(menuai, entry, device)
        runtime_data.block.async_setup()
        runtime_data.rest = ShellyRestCoordinator(menuai, device, entry)
        await menuai.config_entries.async_forward_entry_setups(
            entry, runtime_data.platforms
        )
    elif (
        sleep_period is None
        or device_entry is None
        or not er.async_entries_for_device(er.async_get(menuai), device_entry.id)
    ):
        # Need to get sleep info or first time sleeping device setup, wait for device
        # If there are no entities for the device, it means we added the device, but
        # MenuAI was restarted before the device was online. In this case we
        # cannot restore the entities, so we need to wait for the device to be online.
        LOGGER.debug(
            "Setup for device %s will resume when device is online", entry.title
        )
        runtime_data.block = ShellyBlockCoordinator(menuai, entry, device)
        runtime_data.block.async_setup(runtime_data.platforms)
    else:
        # Restore sensors for sleeping device
        LOGGER.debug("Setting up offline block device %s", entry.title)
        runtime_data.block = ShellyBlockCoordinator(menuai, entry, device)
        runtime_data.block.async_setup()
        await menuai.config_entries.async_forward_entry_setups(
            entry, runtime_data.platforms
        )

    ir.async_delete_issue(
        menuai, DOMAIN, FIRMWARE_UNSUPPORTED_ISSUE_ID.format(unique=entry.unique_id)
    )
    return True


async def _async_setup_rpc_entry(menuai: menuai, entry: ShellyConfigEntry) -> bool:
    """Set up Shelly RPC based device from a config entry."""
    options = ConnectionOptions(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
        device_mac=entry.unique_id,
        port=get_http_port(entry.data),
    )

    ws_context = await get_ws_context(menuai)

    device = await RpcDevice.create(
        async_get_clientsession(menuai),
        ws_context,
        options,
    )

    dev_reg = dr.async_get(menuai)
    device_entry = None
    if entry.unique_id is not None:
        device_entry = dev_reg.async_get_device(
            connections={(CONNECTION_NETWORK_MAC, dr.format_mac(entry.unique_id))},
        )
    # https://github.com/home-assistant/core/pull/48076
    if device_entry and entry.entry_id not in device_entry.config_entries:
        device_entry = None

    sleep_period = entry.data.get(CONF_SLEEP_PERIOD)
    runtime_data = entry.runtime_data
    runtime_data.platforms = RPC_SLEEPING_PLATFORMS

    if sleep_period == 0:
        # Not a sleeping device, finish setup
        LOGGER.debug("Setting up online RPC device %s", entry.title)
        runtime_data.platforms = PLATFORMS
        try:
            await device.initialize()
            if not device.firmware_supported:
                async_create_issue_unsupported_firmware(menuai, entry)
                await device.shutdown()
                raise ConfigEntryNotReady(
                    translation_domain=DOMAIN,
                    translation_key="firmware_unsupported",
                    translation_placeholders={"device": entry.title},
                )
            runtime_data.rpc_zigbee_enabled = device.zigbee_enabled
            runtime_data.rpc_supports_scripts = await device.supports_scripts()
            if runtime_data.rpc_supports_scripts:
                runtime_data.rpc_script_events = await get_rpc_scripts_event_types(
                    device, ignore_scripts=[BLE_SCRIPT_NAME]
                )
        except (DeviceConnectionError, MacAddressMismatchError, RpcCallError) as err:
            await device.shutdown()
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="device_communication_error",
                translation_placeholders={"device": entry.title},
            ) from err
        except InvalidAuthError as err:
            await device.shutdown()
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_error",
                translation_placeholders={"device": entry.title},
            ) from err

        runtime_data.rpc = ShellyRpcCoordinator(menuai, entry, device)
        runtime_data.rpc.async_setup()
        runtime_data.rpc_poll = ShellyRpcPollingCoordinator(menuai, entry, device)
        await menuai.config_entries.async_forward_entry_setups(
            entry, runtime_data.platforms
        )
        async_manage_ble_scanner_firmware_unsupported_issue(
            menuai,
            entry,
        )
    elif (
        sleep_period is None
        or device_entry is None
        or not er.async_entries_for_device(er.async_get(menuai), device_entry.id)
    ):
        # Need to get sleep info or first time sleeping device setup, wait for device
        # If there are no entities for the device, it means we added the device, but
        # MenuAI was restarted before the device was online. In this case we
        # cannot restore the entities, so we need to wait for the device to be online.
        LOGGER.debug(
            "Setup for device %s will resume when device is online", entry.title
        )
        runtime_data.rpc = ShellyRpcCoordinator(menuai, entry, device)
        runtime_data.rpc.async_setup(runtime_data.platforms)
        # Try to connect to the device, if we reached here from config flow
        # and user woke up the device when adding it, we can continue setup
        # otherwise we will wait for the device to wake up
        if sleep_period:
            await runtime_data.rpc.async_device_online("setup")
    else:
        # Restore sensors for sleeping device
        LOGGER.debug("Setting up offline RPC device %s", entry.title)
        runtime_data.rpc = ShellyRpcCoordinator(menuai, entry, device)
        runtime_data.rpc.async_setup()
        await menuai.config_entries.async_forward_entry_setups(
            entry, runtime_data.platforms
        )

    ir.async_delete_issue(
        menuai, DOMAIN, FIRMWARE_UNSUPPORTED_ISSUE_ID.format(unique=entry.unique_id)
    )
    return True


async def async_unload_entry(menuai: menuai, entry: ShellyConfigEntry) -> bool:
    """Unload a config entry."""
    # delete push update issue if it exists
    LOGGER.debug(
        "Deleting issue %s", PUSH_UPDATE_ISSUE_ID.format(unique=entry.unique_id)
    )
    ir.async_delete_issue(
        menuai, DOMAIN, PUSH_UPDATE_ISSUE_ID.format(unique=entry.unique_id)
    )

    runtime_data = entry.runtime_data

    if runtime_data.rpc:
        await runtime_data.rpc.shutdown()

    if runtime_data.block:
        await runtime_data.block.shutdown()

    return await menuai.config_entries.async_unload_platforms(
        entry, runtime_data.platforms
    )


async def async_remove_entry(menuai: menuai, entry: ShellyConfigEntry) -> None:
    """Remove a config entry."""
    if get_device_entry_gen(entry) in RPC_GENERATIONS and (
        mac_address := entry.unique_id
    ):
        source = dr.format_mac(bluetooth_mac_from_primary_mac(mac_address)).upper()
        async_remove_scanner(menuai, source)
