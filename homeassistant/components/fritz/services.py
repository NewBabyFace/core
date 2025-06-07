"""Services for Fritz integration."""

import logging

from fritzconnection.core.exceptions import (
    FritzActionError,
    FritzConnectionException,
    FritzServiceError,
)
from fritzconnection.lib.fritzwlan import DEFAULT_PASSWORD_LENGTH
import voluptuous as vol

from menuai.core import menuai, ServiceCall
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers.service import async_extract_config_entry_ids

from .const import DOMAIN
from .coordinator import FritzConfigEntry

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_GUEST_WIFI_PW = "set_guest_wifi_password"
SERVICE_SCHEMA_SET_GUEST_WIFI_PW = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Optional("password"): vol.Length(min=8, max=63),
        vol.Optional("length"): vol.Range(min=8, max=63),
    }
)


async def _async_set_guest_wifi_password(service_call: ServiceCall) -> None:
    """Call Fritz set guest wifi password service."""
    menuai = service_call.menuai
    target_entry_ids = await async_extract_config_entry_ids(menuai, service_call)
    target_entries: list[FritzConfigEntry] = [
        loaded_entry
        for loaded_entry in menuai.config_entries.async_loaded_entries(DOMAIN)
        if loaded_entry.entry_id in target_entry_ids
    ]

    if not target_entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_found",
            translation_placeholders={"service": service_call.service},
        )

    for target_entry in target_entries:
        _LOGGER.debug("Executing service %s", service_call.service)
        avm_wrapper = target_entry.runtime_data
        try:
            await avm_wrapper.async_trigger_set_guest_password(
                service_call.data.get("password"),
                service_call.data.get("length", DEFAULT_PASSWORD_LENGTH),
            )
        except (FritzServiceError, FritzActionError) as ex:
            raise menuaiError(
                translation_domain=DOMAIN, translation_key="service_parameter_unknown"
            ) from ex
        except FritzConnectionException as ex:
            raise menuaiError(
                translation_domain=DOMAIN, translation_key="service_not_supported"
            ) from ex


async def async_setup_services(menuai: menuai) -> None:
    """Set up services for Fritz integration."""

    menuai.services.async_register(
        DOMAIN,
        SERVICE_SET_GUEST_WIFI_PW,
        _async_set_guest_wifi_password,
        SERVICE_SCHEMA_SET_GUEST_WIFI_PW,
    )
