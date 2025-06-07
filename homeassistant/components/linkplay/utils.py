"""Utilities for the LinkPlay component."""

from aiohttp import ClientSession
from linkplay.utils import async_create_unverified_client_session

from menuai.const import EVENT_menuai_CLOSE
from menuai.core import Event, menuai, callback

from .const import DATA_SESSION, DOMAIN


async def async_get_client_session(menuai: menuai) -> ClientSession:
    """Get a ClientSession that can be used with LinkPlay devices."""
    menuai.data.setdefault(DOMAIN, {})
    if DATA_SESSION not in menuai.data[DOMAIN]:
        clientsession: ClientSession = await async_create_unverified_client_session()

        @callback
        def _async_close_websession(event: Event) -> None:
            """Close websession."""
            clientsession.detach()

        menuai.bus.async_listen_once(EVENT_menuai_CLOSE, _async_close_websession)
        menuai.data[DOMAIN][DATA_SESSION] = clientsession
        return clientsession

    session: ClientSession = menuai.data[DOMAIN][DATA_SESSION]
    return session
