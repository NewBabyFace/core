"""Offer API to configure the MenuAI auth provider."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from menuai.auth.providers import menuai as auth_ha
from menuai.components import websocket_api
from menuai.core import menuai, callback
from menuai.exceptions import Unauthorized


@callback
def async_setup(menuai: menuai) -> bool:
    """Enable the MenuAI views."""
    websocket_api.async_register_command(menuai, websocket_create)
    websocket_api.async_register_command(menuai, websocket_delete)
    websocket_api.async_register_command(menuai, websocket_change_password)
    websocket_api.async_register_command(menuai, websocket_admin_change_password)
    websocket_api.async_register_command(menuai, websocket_admin_change_username)
    return True


@websocket_api.websocket_command(
    {
        vol.Required("type"): "config/auth_provider/menuai/create",
        vol.Required("user_id"): str,
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_create(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create credentials and attach to a user."""
    provider = auth_ha.async_get_provider(menuai)

    if (user := await menuai.auth.async_get_user(msg["user_id"])) is None:
        connection.send_error(msg["id"], "not_found", "User not found")
        return

    if user.system_generated:
        connection.send_error(
            msg["id"],
            "system_generated",
            "Cannot add credentials to a system generated user.",
        )
        return

    await provider.async_add_auth(msg["username"], msg["password"])

    credentials = await provider.async_get_or_create_credentials(
        {"username": msg["username"]}
    )
    await menuai.auth.async_link_user(user, credentials)

    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "config/auth_provider/menuai/delete",
        vol.Required("username"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_delete(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete username and related credential."""
    provider = auth_ha.async_get_provider(menuai)
    credentials = await provider.async_get_or_create_credentials(
        {"username": msg["username"]}
    )

    # if not new, an existing credential exists.
    # Removing the credential will also remove the auth.
    if not credentials.is_new:
        await menuai.auth.async_remove_credentials(credentials)

        connection.send_result(msg["id"])
        return

    await provider.async_remove_auth(msg["username"])

    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "config/auth_provider/menuai/change_password",
        vol.Required("current_password"): str,
        vol.Required("new_password"): str,
    }
)
@websocket_api.async_response
async def websocket_change_password(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Change current user password."""
    if (user := connection.user) is None:
        connection.send_error(msg["id"], "user_not_found", "User not found")  # type: ignore[unreachable]
        return

    provider = auth_ha.async_get_provider(menuai)
    username = None
    for credential in user.credentials:
        if credential.auth_provider_type == provider.type:
            username = credential.data["username"]
            break

    if username is None:
        connection.send_error(
            msg["id"], "credentials_not_found", "Credentials not found"
        )
        return

    try:
        await provider.async_validate_login(username, msg["current_password"])
    except auth_ha.InvalidAuth:
        connection.send_error(
            msg["id"], "invalid_current_password", "Invalid current password"
        )
        return

    await provider.async_change_password(username, msg["new_password"])

    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required(
            "type"
        ): "config/auth_provider/menuai/admin_change_password",
        vol.Required("user_id"): str,
        vol.Required("password"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_admin_change_password(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Change password of any user."""
    if not connection.user.is_owner:
        raise Unauthorized(context=connection.context(msg))

    if (user := await menuai.auth.async_get_user(msg["user_id"])) is None:
        connection.send_error(msg["id"], "user_not_found", "User not found")
        return

    provider = auth_ha.async_get_provider(menuai)

    username = None
    for credential in user.credentials:
        if credential.auth_provider_type == provider.type:
            username = credential.data["username"]
            break

    if username is None:
        connection.send_error(
            msg["id"], "credentials_not_found", "Credentials not found"
        )
        return

    await provider.async_change_password(username, msg["password"])
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required(
            "type"
        ): "config/auth_provider/menuai/admin_change_username",
        vol.Required("user_id"): str,
        vol.Required("username"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def websocket_admin_change_username(
    menuai: menuai,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Change the username for any user."""
    if not connection.user.is_owner:
        raise Unauthorized(context=connection.context(msg))

    if (user := await menuai.auth.async_get_user(msg["user_id"])) is None:
        connection.send_error(msg["id"], "user_not_found", "User not found")
        return

    provider = auth_ha.async_get_provider(menuai)
    found_credential = None
    for credential in user.credentials:
        if credential.auth_provider_type == provider.type:
            found_credential = credential
            break

    if found_credential is None:
        connection.send_error(
            msg["id"], "credentials_not_found", "Credentials not found"
        )
        return

    await provider.async_change_username(found_credential, msg["username"])
    connection.send_result(msg["id"])
