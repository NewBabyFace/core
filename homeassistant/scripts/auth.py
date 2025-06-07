"""Script to manage users for the MenuAI auth provider."""

import argparse
import asyncio
from collections.abc import Sequence
import logging
import os
from typing import TYPE_CHECKING

from menuai import runner
from menuai.auth import auth_manager_from_config
from menuai.auth.providers import menuai as menuai_auth
from menuai.config import get_default_config_dir
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

# mypy: allow-untyped-calls, allow-untyped-defs


def run(args: Sequence[str] | None) -> None:
    """Handle MenuAI auth provider script."""
    parser = argparse.ArgumentParser(description="Manage MenuAI users")
    parser.add_argument("--script", choices=["auth"])
    parser.add_argument(
        "-c",
        "--config",
        default=get_default_config_dir(),
        help="Directory that contains the MenuAI configuration",
    )

    subparsers = parser.add_subparsers(dest="func")
    subparsers.required = True
    parser_list = subparsers.add_parser("list")
    parser_list.set_defaults(func=list_users)

    parser_add = subparsers.add_parser("add")
    parser_add.add_argument("username", type=str)
    parser_add.add_argument("password", type=str)
    parser_add.set_defaults(func=add_user)

    parser_validate_login = subparsers.add_parser("validate")
    parser_validate_login.add_argument("username", type=str)
    parser_validate_login.add_argument("password", type=str)
    parser_validate_login.set_defaults(func=validate_login)

    parser_change_pw = subparsers.add_parser("change_password")
    parser_change_pw.add_argument("username", type=str)
    parser_change_pw.add_argument("new_password", type=str)
    parser_change_pw.set_defaults(func=change_password)

    asyncio.set_event_loop_policy(runner.menuaiEventLoopPolicy(False))
    asyncio.run(run_command(parser.parse_args(args)))


async def run_command(args: argparse.Namespace) -> None:
    """Run the command."""
    menuai = menuai(os.path.join(os.getcwd(), args.config))
    await asyncio.gather(dr.async_load(menuai), er.async_load(menuai))
    menuai.auth = await auth_manager_from_config(menuai, [{"type": "menuai"}], [])
    provider = menuai.auth.auth_providers[0]
    await provider.async_initialize()
    await args.func(menuai, provider, args)

    # Triggers save on used storage helpers with delay (core auth)
    logging.getLogger("menuai.core").setLevel(logging.WARNING)

    await menuai.async_stop()


async def list_users(
    menuai: menuai, provider: menuai_auth.menuaiAuthProvider, args: argparse.Namespace
) -> None:
    """List the users."""
    count = 0
    if TYPE_CHECKING:
        assert provider.data
    for user in provider.data.users:
        count += 1
        print(user["username"])

    print()
    print("Total users:", count)


async def add_user(
    menuai: menuai, provider: menuai_auth.menuaiAuthProvider, args: argparse.Namespace
) -> None:
    """Create a user."""
    if TYPE_CHECKING:
        assert provider.data
    try:
        provider.data.add_auth(args.username, args.password)
    except menuai_auth.InvalidUser:
        print("Username already exists!")
        return

    # Save username/password
    await provider.data.async_save()
    print("Auth created")


async def validate_login(
    menuai: menuai, provider: menuai_auth.menuaiAuthProvider, args: argparse.Namespace
) -> None:
    """Validate a login."""
    if TYPE_CHECKING:
        assert provider.data
    try:
        provider.data.validate_login(args.username, args.password)
        print("Auth valid")
    except menuai_auth.InvalidAuth:
        print("Auth invalid")


async def change_password(
    menuai: menuai, provider: menuai_auth.menuaiAuthProvider, args: argparse.Namespace
) -> None:
    """Change password."""
    if TYPE_CHECKING:
        assert provider.data
    try:
        provider.data.change_password(args.username, args.new_password)
        await provider.data.async_save()
        print("Password changed")
    except menuai_auth.InvalidUser:
        print("User not found")
