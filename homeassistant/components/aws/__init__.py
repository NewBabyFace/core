"""Support for Amazon Web Services (AWS)."""

import asyncio
from collections import OrderedDict
import logging

from aiobotocore.session import AioSession
import voluptuous as vol

from menuai import config_entries
from menuai.config_entries import ConfigEntry
from menuai.const import (
    ATTR_CREDENTIALS,
    CONF_NAME,
    CONF_PROFILE_NAME,
    CONF_SERVICE,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

# Loading the config flow file will register the flow
from .const import (
    CONF_ACCESS_KEY_ID,
    CONF_CONTEXT,
    CONF_CREDENTIAL_NAME,
    CONF_CREDENTIALS,
    CONF_NOTIFY,
    CONF_REGION,
    CONF_SECRET_ACCESS_KEY,
    CONF_VALIDATE,
    DATA_CONFIG,
    DATA_menuai_CONFIG,
    DATA_SESSIONS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

AWS_CREDENTIAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Inclusive(CONF_ACCESS_KEY_ID, ATTR_CREDENTIALS): cv.string,
        vol.Inclusive(CONF_SECRET_ACCESS_KEY, ATTR_CREDENTIALS): cv.string,
        vol.Exclusive(CONF_PROFILE_NAME, ATTR_CREDENTIALS): cv.string,
        vol.Optional(CONF_VALIDATE, default=True): cv.boolean,
    }
)

DEFAULT_CREDENTIAL = [
    {CONF_NAME: "default", CONF_PROFILE_NAME: "default", CONF_VALIDATE: False}
]

SUPPORTED_SERVICES = ["lambda", "sns", "sqs", "events"]

NOTIFY_PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_SERVICE): vol.All(
            cv.string, vol.Lower, vol.In(SUPPORTED_SERVICES)
        ),
        vol.Required(CONF_REGION): vol.All(cv.string, vol.Lower),
        vol.Inclusive(CONF_ACCESS_KEY_ID, ATTR_CREDENTIALS): cv.string,
        vol.Inclusive(CONF_SECRET_ACCESS_KEY, ATTR_CREDENTIALS): cv.string,
        vol.Exclusive(CONF_PROFILE_NAME, ATTR_CREDENTIALS): cv.string,
        vol.Exclusive(CONF_CREDENTIAL_NAME, ATTR_CREDENTIALS): cv.string,
        vol.Optional(CONF_CONTEXT): vol.Coerce(dict),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_CREDENTIALS, default=DEFAULT_CREDENTIAL): vol.All(
                    cv.ensure_list, [AWS_CREDENTIAL_SCHEMA]
                ),
                vol.Optional(CONF_NOTIFY, default=[]): vol.All(
                    cv.ensure_list, [NOTIFY_PLATFORM_SCHEMA]
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up AWS component."""
    menuai.data[DATA_menuai_CONFIG] = config

    if (conf := config.get(DOMAIN)) is None:
        # create a default conf using default profile
        conf = CONFIG_SCHEMA({ATTR_CREDENTIALS: DEFAULT_CREDENTIAL})

    menuai.data[DATA_CONFIG] = conf
    menuai.data[DATA_SESSIONS] = OrderedDict()

    menuai.async_create_task(
        menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=conf
        )
    )

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Load a config entry.

    Validate and save sessions per aws credential.
    """
    config = menuai.data[DATA_menuai_CONFIG]
    conf = menuai.data[DATA_CONFIG]

    if entry.source == config_entries.SOURCE_IMPORT:
        if conf is None:
            # user removed config from configuration.yaml, abort setup
            menuai.async_create_task(menuai.config_entries.async_remove(entry.entry_id))
            return False

        if conf != entry.data:
            # user changed config from configuration.yaml, use conf to setup
            menuai.config_entries.async_update_entry(entry, data=conf)

    if conf is None:
        conf = CONFIG_SCHEMA({DOMAIN: entry.data})[DOMAIN]

    # validate credentials and create sessions
    validation = True
    tasks = [_validate_aws_credentials(menuai, cred) for cred in conf[ATTR_CREDENTIALS]]
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for index, result in enumerate(results):
            name = conf[ATTR_CREDENTIALS][index][CONF_NAME]
            if isinstance(result, Exception):
                _LOGGER.error(
                    "Validating credential [%s] failed: %s",
                    name,
                    result,
                    exc_info=result,
                )
                validation = False
            else:
                menuai.data[DATA_SESSIONS][name] = result

    # set up notify platform, no entry support for notify component yet,
    # have to use discovery to load platform.
    for notify_config in conf[CONF_NOTIFY]:
        menuai.async_create_task(
            discovery.async_load_platform(
                menuai, Platform.NOTIFY, DOMAIN, notify_config, config
            )
        )

    return validation


async def _validate_aws_credentials(menuai, credential):
    """Validate AWS credential config."""
    aws_config = credential.copy()
    del aws_config[CONF_NAME]
    del aws_config[CONF_VALIDATE]

    if (profile := aws_config.get(CONF_PROFILE_NAME)) is not None:
        session = AioSession(profile=profile)
        del aws_config[CONF_PROFILE_NAME]
        if CONF_ACCESS_KEY_ID in aws_config:
            del aws_config[CONF_ACCESS_KEY_ID]
        if CONF_SECRET_ACCESS_KEY in aws_config:
            del aws_config[CONF_SECRET_ACCESS_KEY]
    else:
        session = AioSession()

    if credential[CONF_VALIDATE]:
        async with session.create_client("iam", **aws_config) as client:
            await client.get_user()

    return session
