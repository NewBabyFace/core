"""Support to interact with Remember The Milk."""

from rtmapi import Rtm
import voluptuous as vol

from menuai.components import configurator
from menuai.const import CONF_API_KEY, CONF_ID, CONF_NAME
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.entity_component import EntityComponent
from menuai.helpers.typing import ConfigType

from .const import LOGGER
from .entity import RememberTheMilkEntity
from .storage import RememberTheMilkConfiguration

# httplib2 is a transitive dependency from RtmAPI. If this dependency is not
# set explicitly, the library does not work.

DOMAIN = "remember_the_milk"

CONF_SHARED_SECRET = "shared_secret"

RTM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_SHARED_SECRET): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [RTM_SCHEMA])}, extra=vol.ALLOW_EXTRA
)

SERVICE_CREATE_TASK = "create_task"
SERVICE_COMPLETE_TASK = "complete_task"

SERVICE_SCHEMA_CREATE_TASK = vol.Schema(
    {vol.Required(CONF_NAME): cv.string, vol.Optional(CONF_ID): cv.string}
)

SERVICE_SCHEMA_COMPLETE_TASK = vol.Schema({vol.Required(CONF_ID): cv.string})


def setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Remember the milk component."""
    component = EntityComponent[RememberTheMilkEntity](LOGGER, DOMAIN, menuai)

    stored_rtm_config = RememberTheMilkConfiguration(menuai)
    for rtm_config in config[DOMAIN]:
        account_name = rtm_config[CONF_NAME]
        LOGGER.debug("Adding Remember the milk account %s", account_name)
        api_key = rtm_config[CONF_API_KEY]
        shared_secret = rtm_config[CONF_SHARED_SECRET]
        token = stored_rtm_config.get_token(account_name)
        if token:
            LOGGER.debug("found token for account %s", account_name)
            _create_instance(
                menuai,
                account_name,
                api_key,
                shared_secret,
                token,
                stored_rtm_config,
                component,
            )
        else:
            _register_new_account(
                menuai, account_name, api_key, shared_secret, stored_rtm_config, component
            )

    LOGGER.debug("Finished adding all Remember the milk accounts")
    return True


def _create_instance(
    menuai: menuai,
    account_name: str,
    api_key: str,
    shared_secret: str,
    token: str,
    stored_rtm_config: RememberTheMilkConfiguration,
    component: EntityComponent[RememberTheMilkEntity],
) -> None:
    entity = RememberTheMilkEntity(
        account_name, api_key, shared_secret, token, stored_rtm_config
    )
    component.add_entities([entity])
    menuai.services.register(
        DOMAIN,
        f"{account_name}_create_task",
        entity.create_task,
        schema=SERVICE_SCHEMA_CREATE_TASK,
    )
    menuai.services.register(
        DOMAIN,
        f"{account_name}_complete_task",
        entity.complete_task,
        schema=SERVICE_SCHEMA_COMPLETE_TASK,
    )


def _register_new_account(
    menuai: menuai,
    account_name: str,
    api_key: str,
    shared_secret: str,
    stored_rtm_config: RememberTheMilkConfiguration,
    component: EntityComponent[RememberTheMilkEntity],
) -> None:
    api = Rtm(api_key, shared_secret, "write", None)
    url, frob = api.authenticate_desktop()
    LOGGER.debug("Sent authentication request to server")

    def register_account_callback(fields: list[dict[str, str]]) -> None:
        """Call for register the configurator."""
        api.retrieve_token(frob)
        token = api.token
        if api.token is None:
            LOGGER.error("Failed to register, please try again")
            configurator.notify_errors(
                menuai, request_id, "Failed to register, please try again."
            )
            return

        stored_rtm_config.set_token(account_name, token)
        LOGGER.debug("Retrieved new token from server")

        _create_instance(
            menuai,
            account_name,
            api_key,
            shared_secret,
            token,
            stored_rtm_config,
            component,
        )

        configurator.request_done(menuai, request_id)

    request_id = configurator.request_config(
        menuai,
        f"{DOMAIN} - {account_name}",
        callback=register_account_callback,
        description=(
            "You need to log in to Remember The Milk to"
            "connect your account. \n\n"
            "Step 1: Click on the link 'Remember The Milk login'\n\n"
            "Step 2: Click on 'login completed'"
        ),
        link_name="Remember The Milk login",
        link_url=url,
        submit_caption="login completed",
    )
