"""Config flow for iOS."""

from menuai.helpers import config_entry_flow

from .const import DOMAIN

config_entry_flow.register_discovery_flow(
    DOMAIN, "MenuAI iOS", lambda menuai: True
)
