"""The Smappee integration."""

from pysmappee import Smappee, helper, mqtt
import voluptuous as vol

from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_IP_ADDRESS,
    CONF_PLATFORM,
)
from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow, config_validation as cv
from menuai.helpers.typing import ConfigType
from menuai.util import Throttle

from . import api, config_flow
from .const import (
    AUTHORIZE_URL,
    CONF_SERIALNUMBER,
    DOMAIN,
    MIN_TIME_BETWEEN_UPDATES,
    PLATFORMS,
    TOKEN_URL,
)

type SmappeeConfigEntry = ConfigEntry[SmappeeBase]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Smappee component."""
    menuai.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    client_id = config[DOMAIN][CONF_CLIENT_ID]
    menuai.data[DOMAIN][client_id] = {}

    # decide platform
    platform = "PRODUCTION"
    if client_id == "menuai_f2":
        platform = "ACCEPTANCE"
    elif client_id == "menuai_f3":
        platform = "DEVELOPMENT"

    menuai.data[DOMAIN][CONF_PLATFORM] = platform

    config_flow.SmappeeFlowHandler.async_register_implementation(
        menuai,
        config_entry_oauth2_flow.LocalOAuth2Implementation(
            menuai,
            DOMAIN,
            config[DOMAIN][CONF_CLIENT_ID],
            config[DOMAIN][CONF_CLIENT_SECRET],
            AUTHORIZE_URL[platform],
            TOKEN_URL[platform],
        ),
    )

    return True


async def async_setup_entry(menuai: menuai, entry: SmappeeConfigEntry) -> bool:
    """Set up Smappee from a zeroconf or config entry."""
    if CONF_IP_ADDRESS in entry.data:
        if helper.is_smappee_genius(entry.data[CONF_SERIALNUMBER]):
            # next generation: local mqtt broker
            smappee_mqtt = mqtt.SmappeeLocalMqtt(
                serial_number=entry.data[CONF_SERIALNUMBER]
            )
            await menuai.async_add_executor_job(smappee_mqtt.start_and_wait_for_config)
            smappee = Smappee(
                api=smappee_mqtt, serialnumber=entry.data[CONF_SERIALNUMBER]
            )
        else:
            # legacy devices through local api
            smappee_api = api.api.SmappeeLocalApi(ip=entry.data[CONF_IP_ADDRESS])
            smappee = Smappee(
                api=smappee_api, serialnumber=entry.data[CONF_SERIALNUMBER]
            )
        await menuai.async_add_executor_job(smappee.load_local_service_location)
    else:
        implementation = (
            await config_entry_oauth2_flow.async_get_config_entry_implementation(
                menuai, entry
            )
        )

        smappee_api = api.ConfigEntrySmappeeApi(menuai, entry, implementation)

        smappee = Smappee(api=smappee_api)
        await menuai.async_add_executor_job(smappee.load_service_locations)

    entry.runtime_data = SmappeeBase(menuai, smappee)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: SmappeeConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


class SmappeeBase:
    """An object to hold the PySmappee instance."""

    def __init__(self, menuai: menuai, smappee: Smappee) -> None:
        """Initialize the Smappee API wrapper class."""
        self.menuai = menuai
        self.smappee = smappee

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self) -> None:
        """Update all Smappee trends and appliance states."""
        await self.menuai.async_add_executor_job(
            self.smappee.update_trends_and_appliance_states
        )
