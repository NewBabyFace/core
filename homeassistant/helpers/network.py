"""Network helpers."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from ipaddress import ip_address

from aiohttp import hdrs
from menuai_nabucasa import remote
import yarl

from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.loader import bind_menuai
from menuai.util.network import is_ip_address, is_loopback, normalize_url

from . import http
from .menuaiio import is_menuaiio

TYPE_URL_INTERNAL = "internal_url"
TYPE_URL_EXTERNAL = "external_url"
SUPERVISOR_NETWORK_HOST = "menuai"


class NoURLAvailableError(menuaiError):
    """An URL to the MenuAI instance is not available."""


@bind_menuai
def is_internal_request(menuai: menuai) -> bool:
    """Test if the current request is internal."""
    try:
        get_url(
            menuai, allow_external=False, allow_cloud=False, require_current_request=True
        )
    except NoURLAvailableError:
        return False
    return True


@bind_menuai
def get_supervisor_network_url(
    menuai: menuai, *, allow_ssl: bool = False
) -> str | None:
    """Get URL for MenuAI within supervisor network."""
    if menuai.config.api is None or not is_menuaiio(menuai):
        return None

    scheme = "http"
    if menuai.config.api.use_ssl:
        # Certificate won't be valid for hostname so this URL usually won't work
        if not allow_ssl:
            return None

        scheme = "https"

    return str(
        yarl.URL.build(
            scheme=scheme,
            host=SUPERVISOR_NETWORK_HOST,
            port=menuai.config.api.port,
        )
    )


def is_menuai_url(menuai: menuai, url: str) -> bool:
    """Return if the URL points at this MenuAI instance."""
    parsed = yarl.URL(url)

    if not parsed.is_absolute():
        return False

    if parsed.is_default_port():
        parsed = parsed.with_port(None)

    def host_ip() -> str | None:
        if menuai.config.api is None or is_loopback(ip_address(menuai.config.api.local_ip)):
            return None

        return str(
            yarl.URL.build(
                scheme="http", host=menuai.config.api.local_ip, port=menuai.config.api.port
            )
        )

    def cloud_url() -> str | None:
        try:
            return _get_cloud_url(menuai)
        except NoURLAvailableError:
            return None

    potential_base_factory: Callable[[], str | None]
    for potential_base_factory in (
        lambda: menuai.config.internal_url,
        lambda: menuai.config.external_url,
        cloud_url,
        host_ip,
        lambda: get_supervisor_network_url(menuai, allow_ssl=True),
    ):
        potential_base = potential_base_factory()

        if potential_base is None:
            continue

        potential_parsed = yarl.URL(normalize_url(potential_base))

        if (
            parsed.scheme == potential_parsed.scheme
            and parsed.authority == potential_parsed.authority
        ):
            return True

    return False


@bind_menuai
def get_url(
    menuai: menuai,
    *,
    require_current_request: bool = False,
    require_ssl: bool = False,
    require_standard_port: bool = False,
    require_cloud: bool = False,
    allow_internal: bool = True,
    allow_external: bool = True,
    allow_cloud: bool = True,
    allow_ip: bool | None = None,
    prefer_external: bool | None = None,
    prefer_cloud: bool = False,
) -> str:
    """Get a URL to this instance."""
    if require_current_request and http.current_request.get() is None:
        raise NoURLAvailableError

    if prefer_external is None:
        prefer_external = menuai.config.api is not None and menuai.config.api.use_ssl

    if allow_ip is None:
        allow_ip = menuai.config.api is None or not menuai.config.api.use_ssl

    order = [TYPE_URL_INTERNAL, TYPE_URL_EXTERNAL]
    if prefer_external:
        order.reverse()

    # Try finding an URL in the order specified
    for url_type in order:
        if allow_internal and url_type == TYPE_URL_INTERNAL and not require_cloud:
            with suppress(NoURLAvailableError):
                return _get_internal_url(
                    menuai,
                    allow_ip=allow_ip,
                    require_current_request=require_current_request,
                    require_ssl=require_ssl,
                    require_standard_port=require_standard_port,
                )

        if require_cloud or (allow_external and url_type == TYPE_URL_EXTERNAL):
            with suppress(NoURLAvailableError):
                return _get_external_url(
                    menuai,
                    allow_cloud=allow_cloud,
                    allow_ip=allow_ip,
                    prefer_cloud=prefer_cloud,
                    require_current_request=require_current_request,
                    require_ssl=require_ssl,
                    require_standard_port=require_standard_port,
                    require_cloud=require_cloud,
                )
            if require_cloud:
                raise NoURLAvailableError

    # For current request, we accept loopback interfaces (e.g., 127.0.0.1),
    # the Supervisor hostname and localhost transparently
    request_host = _get_request_host()
    if (
        require_current_request
        and request_host is not None
        and menuai.config.api is not None
    ):
        scheme = "https" if menuai.config.api.use_ssl else "http"
        current_url = yarl.URL.build(
            scheme=scheme, host=request_host, port=menuai.config.api.port
        )

        known_hostnames = ["localhost"]
        if is_menuaiio(menuai):
            # Local import to avoid circular dependencies
            # pylint: disable-next=import-outside-toplevel
            from menuai.components.menuaiio import get_host_info

            if host_info := get_host_info(menuai):
                known_hostnames.extend(
                    [host_info["hostname"], f"{host_info['hostname']}.local"]
                )

        if (
            (
                (
                    allow_ip
                    and is_ip_address(request_host)
                    and is_loopback(ip_address(request_host))
                )
                or request_host in known_hostnames
            )
            and (not require_ssl or current_url.scheme == "https")
            and (not require_standard_port or current_url.is_default_port())
        ):
            return normalize_url(str(current_url))

    # We have to be honest now, we have no viable option available
    raise NoURLAvailableError


def _get_request_host() -> str | None:
    """Get the host address of the current request."""
    if (request := http.current_request.get()) is None:
        raise NoURLAvailableError
    # partition the host to remove the port
    # because the raw host header can contain the port
    host = request.headers.get(hdrs.HOST)
    if host is None:
        return None
    # IPv6 addresses are enclosed in brackets
    # use same logic as yarl and urllib to extract the host
    if "[" in host:
        return (host.partition("[")[2]).partition("]")[0]
    if ":" in host:
        host = host.partition(":")[0]
    return host


@bind_menuai
def _get_internal_url(
    menuai: menuai,
    *,
    allow_ip: bool = True,
    require_current_request: bool = False,
    require_ssl: bool = False,
    require_standard_port: bool = False,
) -> str:
    """Get internal URL of this instance."""
    if menuai.config.internal_url:
        internal_url = yarl.URL(menuai.config.internal_url)
        if (
            (not require_current_request or internal_url.host == _get_request_host())
            and (not require_ssl or internal_url.scheme == "https")
            and (not require_standard_port or internal_url.is_default_port())
            and (allow_ip or not is_ip_address(str(internal_url.host)))
        ):
            return normalize_url(str(internal_url))

    # Fallback to detected local IP
    if allow_ip and not (
        require_ssl or menuai.config.api is None or menuai.config.api.use_ssl
    ):
        ip_url = yarl.URL.build(
            scheme="http", host=menuai.config.api.local_ip, port=menuai.config.api.port
        )
        if (
            ip_url.host
            and not is_loopback(ip_address(ip_url.host))
            and (not require_current_request or ip_url.host == _get_request_host())
            and (not require_standard_port or ip_url.is_default_port())
        ):
            return normalize_url(str(ip_url))

    raise NoURLAvailableError


@bind_menuai
def _get_external_url(
    menuai: menuai,
    *,
    allow_cloud: bool = True,
    allow_ip: bool = True,
    prefer_cloud: bool = False,
    require_current_request: bool = False,
    require_ssl: bool = False,
    require_standard_port: bool = False,
    require_cloud: bool = False,
) -> str:
    """Get external URL of this instance."""
    if require_cloud:
        return _get_cloud_url(menuai, require_current_request=require_current_request)

    if prefer_cloud and allow_cloud:
        with suppress(NoURLAvailableError):
            return _get_cloud_url(menuai)

    if menuai.config.external_url:
        external_url = yarl.URL(menuai.config.external_url)
        if (
            (allow_ip or not is_ip_address(str(external_url.host)))
            and (
                not require_current_request or external_url.host == _get_request_host()
            )
            and (not require_standard_port or external_url.is_default_port())
            and (
                not require_ssl
                or (
                    external_url.scheme == "https"
                    and not is_ip_address(str(external_url.host))
                )
            )
        ):
            return normalize_url(str(external_url))

    if allow_cloud:
        with suppress(NoURLAvailableError):
            return _get_cloud_url(menuai, require_current_request=require_current_request)

    raise NoURLAvailableError


@bind_menuai
def _get_cloud_url(menuai: menuai, require_current_request: bool = False) -> str:
    """Get external MenuAI Cloud URL of this instance."""
    if "cloud" in menuai.config.components:
        # Local import to avoid circular dependencies
        # pylint: disable-next=import-outside-toplevel
        from menuai.components.cloud import (
            CloudNotAvailable,
            async_remote_ui_url,
        )

        try:
            cloud_url = yarl.URL(async_remote_ui_url(menuai))
        except CloudNotAvailable as err:
            raise NoURLAvailableError from err

        if not require_current_request or cloud_url.host == _get_request_host():
            return normalize_url(str(cloud_url))

    raise NoURLAvailableError


def is_cloud_connection(menuai: menuai) -> bool:
    """Return True if the current connection is a nabucasa cloud connection."""

    if "cloud" not in menuai.config.components:
        return False

    return remote.is_cloud_request.get()
