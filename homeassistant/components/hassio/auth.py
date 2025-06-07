"""Implement the auth feature from menuai.io for Add-ons."""

from http import HTTPStatus
from ipaddress import ip_address
import logging
import os

from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound, HTTPUnauthorized
import voluptuous as vol

from menuai.auth.models import User
from menuai.auth.providers import menuai as auth_ha
from menuai.components.http import KEY_menuai, KEY_menuai_USER, menuaiView
from menuai.components.http.data_validator import RequestDataValidator
from menuai.core import menuai, callback
from menuai.helpers import config_validation as cv

from .const import ATTR_ADDON, ATTR_PASSWORD, ATTR_USERNAME

_LOGGER = logging.getLogger(__name__)


@callback
def async_setup_auth_view(menuai: menuai, user: User) -> None:
    """Auth setup."""
    menuaiio_auth = menuaiIOAuth(menuai, user)
    menuaiio_password_reset = menuaiIOPasswordReset(menuai, user)

    menuai.http.register_view(menuaiio_auth)
    menuai.http.register_view(menuaiio_password_reset)


class menuaiIOBaseAuth(menuaiView):
    """menuai.io view to handle auth requests."""

    def __init__(self, menuai: menuai, user: User) -> None:
        """Initialize WebView."""
        self.menuai = menuai
        self.user = user

    def _check_access(self, request: web.Request) -> None:
        """Check if this call is from Supervisor."""
        # Check caller IP
        menuaiio_ip = os.environ["SUPERVISOR"].split(":")[0]
        assert request.transport
        if ip_address(request.transport.get_extra_info("peername")[0]) != ip_address(
            menuaiio_ip
        ):
            _LOGGER.error("Invalid auth request from %s", request.remote)
            raise HTTPUnauthorized

        # Check caller token
        if request[KEY_menuai_USER].id != self.user.id:
            _LOGGER.error("Invalid auth request from %s", request[KEY_menuai_USER].name)
            raise HTTPUnauthorized


class menuaiIOAuth(menuaiIOBaseAuth):
    """menuai.io view to handle auth requests."""

    name = "api:menuaiio:auth"
    url = "/api/menuaiio_auth"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required(ATTR_USERNAME): cv.string,
                vol.Required(ATTR_PASSWORD): cv.string,
                vol.Required(ATTR_ADDON): cv.string,
            },
            extra=vol.ALLOW_EXTRA,
        )
    )
    async def post(self, request: web.Request, data: dict[str, str]) -> web.Response:
        """Handle auth requests."""
        self._check_access(request)
        provider = auth_ha.async_get_provider(request.app[KEY_menuai])

        try:
            await provider.async_validate_login(
                data[ATTR_USERNAME], data[ATTR_PASSWORD]
            )
        except auth_ha.InvalidAuth:
            raise HTTPNotFound from None

        return web.Response(status=HTTPStatus.OK)


class menuaiIOPasswordReset(menuaiIOBaseAuth):
    """menuai.io view to handle password reset requests."""

    name = "api:menuaiio:auth:password:reset"
    url = "/api/menuaiio_auth/password_reset"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required(ATTR_USERNAME): cv.string,
                vol.Required(ATTR_PASSWORD): cv.string,
            },
            extra=vol.ALLOW_EXTRA,
        )
    )
    async def post(self, request: web.Request, data: dict[str, str]) -> web.Response:
        """Handle password reset requests."""
        self._check_access(request)
        provider = auth_ha.async_get_provider(request.app[KEY_menuai])

        try:
            await provider.async_change_password(
                data[ATTR_USERNAME], data[ATTR_PASSWORD]
            )
        except auth_ha.InvalidUser as err:
            raise HTTPNotFound from err

        return web.Response(status=HTTPStatus.OK)
