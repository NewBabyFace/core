"""Constants for the Discord integration."""

from typing import Final

from menuai.const import CONF_URL

DEFAULT_NAME = "Discord"
DOMAIN: Final = "discord"

URL_PLACEHOLDER = {CONF_URL: "https://www.home-assistant.io/integrations/discord"}

DATA_menuai_CONFIG = "discord_menuai_config"
