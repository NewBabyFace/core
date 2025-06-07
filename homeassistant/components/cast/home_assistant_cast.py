"""MenuAI Cast integration for Cast."""

from __future__ import annotations

import voluptuous as vol

from menuai import auth, config_entries, core
from menuai.const import ATTR_ENTITY_ID
from menuai.exceptions import menuaiError
from menuai.helpers import config_validation as cv, dispatcher, instance_id
from menuai.helpers.network import NoURLAvailableError, get_url
from menuai.helpers.service import async_register_admin_service

from .const import DOMAIN, SIGNAL_menuai_CAST_SHOW_VIEW, menuaiControllerData

SERVICE_SHOW_VIEW = "show_lovelace_view"
ATTR_VIEW_PATH = "view_path"
ATTR_URL_PATH = "dashboard_path"
CAST_USER_NAME = "MenuAI Cast"
NO_URL_AVAILABLE_ERROR = (
    "MenuAI Cast requires your instance to be reachable via HTTPS. Enable Home"
    " Assistant Cloud or set up an external URL with valid SSL certificates"
)


async def async_setup_ha_cast(
    menuai: core.menuai, entry: config_entries.ConfigEntry
):
    """Set up MenuAI Cast."""
    user_id: str | None = entry.data.get("user_id")
    user: auth.models.User | None = None

    if user_id is not None:
        user = await menuai.auth.async_get_user(user_id)

    if user is None:
        user = await menuai.auth.async_create_system_user(
            CAST_USER_NAME, group_ids=[auth.const.GROUP_ID_ADMIN]
        )
        menuai.config_entries.async_update_entry(
            entry, data={**entry.data, "user_id": user.id}
        )

    if user.refresh_tokens:
        refresh_token: auth.models.RefreshToken = list(user.refresh_tokens.values())[0]
    else:
        refresh_token = await menuai.auth.async_create_refresh_token(user)

    async def handle_show_view(call: core.ServiceCall) -> None:
        """Handle a Show View service call."""
        try:
            menuai_url = get_url(menuai, require_ssl=True, prefer_external=True)
        except NoURLAvailableError as err:
            raise menuaiError(NO_URL_AVAILABLE_ERROR) from err

        menuai_uuid = await instance_id.async_get(menuai)

        controller_data = menuaiControllerData(
            # If you are developing MenuAI Cast, uncomment and set to
            # your dev app id.
            # app_id="5FE44367",
            menuai_url=menuai_url,
            menuai_uuid=menuai_uuid,
            client_id=None,
            refresh_token=refresh_token.token,
        )

        dispatcher.async_dispatcher_send(
            menuai,
            SIGNAL_menuai_CAST_SHOW_VIEW,
            controller_data,
            call.data[ATTR_ENTITY_ID],
            call.data[ATTR_VIEW_PATH],
            call.data.get(ATTR_URL_PATH),
        )

    async_register_admin_service(
        menuai,
        DOMAIN,
        SERVICE_SHOW_VIEW,
        handle_show_view,
        vol.Schema(
            {
                ATTR_ENTITY_ID: cv.entity_id,
                ATTR_VIEW_PATH: str,
                vol.Optional(ATTR_URL_PATH): str,
            }
        ),
    )


async def async_remove_user(
    menuai: core.menuai, entry: config_entries.ConfigEntry
):
    """Remove MenuAI Cast user."""
    user_id: str | None = entry.data.get("user_id")

    if user_id is not None and (user := await menuai.auth.async_get_user(user_id)):
        await menuai.auth.async_remove_user(user)
