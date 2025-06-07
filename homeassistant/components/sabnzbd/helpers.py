"""Support for the Sabnzbd service."""

from pysabnzbd import SabnzbdApi, SabnzbdApiException

from menuai.const import CONF_API_KEY, CONF_URL
from menuai.core import _LOGGER, menuai
from menuai.helpers.aiohttp_client import async_get_clientsession


async def get_client(menuai: menuai, data):
    """Get Sabnzbd client."""
    api_key = data[CONF_API_KEY]
    url = data[CONF_URL]

    sab_api = SabnzbdApi(
        url,
        api_key,
        session=async_get_clientsession(menuai, False),
    )
    try:
        await sab_api.check_available()
    except SabnzbdApiException as exception:
        _LOGGER.error("Connection to SABnzbd API failed: %s", exception.message)
        return False

    return sab_api
