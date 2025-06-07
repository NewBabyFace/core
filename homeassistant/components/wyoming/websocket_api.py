"""Wyoming Websocket API."""

import logging
from typing import Any

import voluptuous as vol

from menuai.components import websocket_api
from menuai.core import menuai, callback

from .const import DOMAIN
from .models import DomainDataItem

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_websocket_api(menuai: menuai) -> None:
    """Register the websocket API."""
    websocket_api.async_register_command(menuai, websocket_info)


@callback
@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "wyoming/info"})
def websocket_info(
    menuai: menuai,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List service information for Wyoming all config entries."""
    entry_items: dict[str, DomainDataItem] = menuai.data.get(DOMAIN, {})

    connection.send_result(
        msg["id"],
        {
            "info": {
                entry_id: item.service.info.to_dict()
                for entry_id, item in entry_items.items()
            }
        },
    )
