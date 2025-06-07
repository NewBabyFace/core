"""Support for the Foursquare (Swarm) API."""

from http import HTTPStatus
import logging

from aiohttp import web
import requests
import voluptuous as vol

from menuai.components.http import KEY_menuai, menuaiView
from menuai.const import CONF_ACCESS_TOKEN
from menuai.core import menuai, ServiceCall
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

CONF_PUSH_SECRET = "push_secret"

DOMAIN = "foursquare"

EVENT_CHECKIN = "foursquare.checkin"
EVENT_PUSH = "foursquare.push"

SERVICE_CHECKIN = "checkin"

CHECKIN_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("alt"): cv.string,
        vol.Optional("altAcc"): cv.string,
        vol.Optional("broadcast"): cv.string,
        vol.Optional("eventId"): cv.string,
        vol.Optional("ll"): cv.string,
        vol.Optional("llAcc"): cv.string,
        vol.Optional("mentions"): cv.string,
        vol.Optional("shout"): cv.string,
        vol.Required("venueId"): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): cv.string,
                vol.Required(CONF_PUSH_SECRET): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Foursquare component."""
    config = config[DOMAIN]

    def checkin_user(call: ServiceCall) -> None:
        """Check a user in on Swarm."""
        url = f"https://api.foursquare.com/v2/checkins/add?oauth_token={config[CONF_ACCESS_TOKEN]}&v=20160802&m=swarm"
        response = requests.post(url, data=call.data, timeout=10)

        if response.status_code not in (HTTPStatus.OK, HTTPStatus.CREATED):
            _LOGGER.exception(
                "Error checking in user. Response %d: %s:",
                response.status_code,
                response.reason,
            )

        menuai.bus.fire(EVENT_CHECKIN, {"text": response.text})

    # Register our service with MenuAI.
    menuai.services.register(
        DOMAIN, "checkin", checkin_user, schema=CHECKIN_SERVICE_SCHEMA
    )

    menuai.http.register_view(FoursquarePushReceiver(config[CONF_PUSH_SECRET]))

    return True


class FoursquarePushReceiver(menuaiView):
    """Handle pushes from the Foursquare API."""

    requires_auth = False
    url = "/api/foursquare"
    name = "foursquare"

    def __init__(self, push_secret: str) -> None:
        """Initialize the OAuth callback view."""
        self.push_secret = push_secret

    async def post(self, request: web.Request) -> web.Response | None:
        """Accept the POST from Foursquare."""
        try:
            data = await request.json()
        except ValueError:
            return self.json_message("Invalid JSON", HTTPStatus.BAD_REQUEST)

        secret = data.pop("secret", None)

        _LOGGER.debug("Received Foursquare push: %s", data)

        if self.push_secret != secret:
            _LOGGER.error(
                "Received Foursquare push with invalid push secret: %s", secret
            )
            return self.json_message("Incorrect secret", HTTPStatus.BAD_REQUEST)

        request.app[KEY_menuai].bus.async_fire(EVENT_PUSH, data)
        return None
