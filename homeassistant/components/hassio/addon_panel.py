"""Implement the Ingress Panel feature for menuai.io Add-ons."""

from http import HTTPStatus
import logging
from typing import Any

from aiohttp import web

from menuai.components import frontend, panel_custom
from menuai.components.http import menuaiView
from menuai.const import ATTR_ICON
from menuai.core import menuai

from .const import ATTR_ADMIN, ATTR_ENABLE, ATTR_PANELS, ATTR_TITLE
from .handler import menuaiIO, menuaiioAPIError

_LOGGER = logging.getLogger(__name__)


async def async_setup_addon_panel(menuai: menuai, menuaiio: menuaiIO) -> None:
    """Add-on Ingress Panel setup."""
    menuaiio_addon_panel = menuaiIOAddonPanel(menuai, menuaiio)
    menuai.http.register_view(menuaiio_addon_panel)

    # If panels are exists
    if not (panels := await menuaiio_addon_panel.get_panels()):
        return

    # Register available panels
    for addon, data in panels.items():
        if not data[ATTR_ENABLE]:
            continue
        # _register_panel never suspends and is only
        # a coroutine because it would be a breaking change
        # to make it a normal function
        await _register_panel(menuai, addon, data)


class menuaiIOAddonPanel(menuaiView):
    """menuai.io view to handle base part."""

    name = "api:menuaiio_push:panel"
    url = "/api/menuaiio_push/panel/{addon}"

    def __init__(self, menuai: menuai, menuaiio: menuaiIO) -> None:
        """Initialize WebView."""
        self.menuai = menuai
        self.menuaiio = menuaiio

    async def post(self, request: web.Request, addon: str) -> web.Response:
        """Handle new add-on panel requests."""
        panels = await self.get_panels()

        # Panel exists for add-on slug
        if addon not in panels or not panels[addon][ATTR_ENABLE]:
            _LOGGER.error("Panel is not enable for %s", addon)
            return web.Response(status=HTTPStatus.BAD_REQUEST)
        data = panels[addon]

        # Register panel
        await _register_panel(self.menuai, addon, data)
        return web.Response()

    async def delete(self, request: web.Request, addon: str) -> web.Response:
        """Handle remove add-on panel requests."""
        frontend.async_remove_panel(self.menuai, addon)
        return web.Response()

    async def get_panels(self) -> dict:
        """Return panels add-on info data."""
        try:
            data = await self.menuaiio.get_ingress_panels()
            return data[ATTR_PANELS]
        except menuaiioAPIError as err:
            _LOGGER.error("Can't read panel info: %s", err)
        return {}


async def _register_panel(
    menuai: menuai, addon: str, data: dict[str, Any]
) -> None:
    """Init coroutine to register the panel."""
    await panel_custom.async_register_panel(
        menuai,
        frontend_url_path=addon,
        webcomponent_name="menuaiio-main",
        sidebar_title=data[ATTR_TITLE],
        sidebar_icon=data[ATTR_ICON],
        js_url="/api/menuaiio/app/entrypoint.js",
        embed_iframe=True,
        require_admin=data[ATTR_ADMIN],
        config={"ingress": addon},
    )
