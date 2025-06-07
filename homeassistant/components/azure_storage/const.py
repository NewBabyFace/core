"""Constants for the Azure Storage integration."""

from collections.abc import Callable
from typing import Final

from menuai.util.menuai_dict import menuaiKey

DOMAIN: Final = "azure_storage"

CONF_STORAGE_ACCOUNT_KEY: Final = "storage_account_key"
CONF_ACCOUNT_NAME: Final = "account_name"
CONF_CONTAINER_NAME: Final = "container_name"

DATA_BACKUP_AGENT_LISTENERS: menuaiKey[list[Callable[[], None]]] = menuaiKey(
    f"{DOMAIN}.backup_agent_listeners"
)
