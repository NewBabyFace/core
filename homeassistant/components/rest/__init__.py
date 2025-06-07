"""The rest component."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
import contextlib
from datetime import timedelta
import logging
from typing import Any

import httpx
import voluptuous as vol

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.const import (
    CONF_AUTHENTICATION,
    CONF_HEADERS,
    CONF_METHOD,
    CONF_PARAMS,
    CONF_PASSWORD,
    CONF_PAYLOAD,
    CONF_RESOURCE,
    CONF_RESOURCE_TEMPLATE,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    HTTP_DIGEST_AUTHENTICATION,
    SERVICE_RELOAD,
    Platform,
)
from menuai.core import menuai, ServiceCall, callback
from menuai.exceptions import menuaiError
from menuai.helpers import discovery, template
from menuai.helpers.entity_component import DEFAULT_SCAN_INTERVAL
from menuai.helpers.reload import (
    async_integration_yaml_config,
    async_reload_integration_platforms,
)
from menuai.helpers.typing import ConfigType, DiscoveryInfoType
from menuai.helpers.update_coordinator import DataUpdateCoordinator
from menuai.util.async_ import create_eager_task

from .const import (
    CONF_ENCODING,
    CONF_PAYLOAD_TEMPLATE,
    CONF_SSL_CIPHER_LIST,
    COORDINATOR,
    DEFAULT_SSL_CIPHER_LIST,
    DOMAIN,
    PLATFORM_IDX,
    REST,
    REST_DATA,
    REST_IDX,
)
from .data import RestData
from .schema import CONFIG_SCHEMA, RESOURCE_SCHEMA  # noqa: F401

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.NOTIFY,
    Platform.SENSOR,
    Platform.SWITCH,
]

COORDINATOR_AWARE_PLATFORMS = [SENSOR_DOMAIN, BINARY_SENSOR_DOMAIN]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the rest platforms."""
    _async_setup_shared_data(menuai)

    async def reload_service_handler(service: ServiceCall) -> None:
        """Remove all user-defined groups and load new ones from config."""
        conf = None
        with contextlib.suppress(menuaiError):
            conf = await async_integration_yaml_config(menuai, DOMAIN)
        if conf is None:
            return
        await async_reload_integration_platforms(menuai, DOMAIN, PLATFORMS)
        _async_setup_shared_data(menuai)
        await _async_process_config(menuai, conf)

    menuai.services.async_register(
        DOMAIN, SERVICE_RELOAD, reload_service_handler, schema=vol.Schema({})
    )

    return await _async_process_config(menuai, config)


@callback
def _async_setup_shared_data(menuai: menuai) -> None:
    """Create shared data for platform config and rest coordinators."""
    menuai.data[DOMAIN] = {key: [] for key in (REST_DATA, *COORDINATOR_AWARE_PLATFORMS)}


async def _async_process_config(menuai: menuai, config: ConfigType) -> bool:
    """Process rest configuration."""
    if DOMAIN not in config:
        return True

    refresh_coroutines: list[Coroutine[Any, Any, None]] = []
    load_coroutines: list[Coroutine[Any, Any, None]] = []
    rest_config: list[ConfigType] = config[DOMAIN]
    for rest_idx, conf in enumerate(rest_config):
        scan_interval: timedelta = conf.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        resource_template: template.Template | None = conf.get(CONF_RESOURCE_TEMPLATE)
        payload_template: template.Template | None = conf.get(CONF_PAYLOAD_TEMPLATE)
        rest = create_rest_data_from_config(menuai, conf)
        coordinator = _rest_coordinator(
            menuai, rest, resource_template, payload_template, scan_interval
        )
        refresh_coroutines.append(coordinator.async_refresh())
        menuai.data[DOMAIN][REST_DATA].append({REST: rest, COORDINATOR: coordinator})

        for platform_domain in COORDINATOR_AWARE_PLATFORMS:
            if platform_domain not in conf:
                continue

            for platform_conf in conf[platform_domain]:
                menuai.data[DOMAIN][platform_domain].append(platform_conf)
                platform_idx = len(menuai.data[DOMAIN][platform_domain]) - 1

                load_coroutine = discovery.async_load_platform(
                    menuai,
                    platform_domain,
                    DOMAIN,
                    {REST_IDX: rest_idx, PLATFORM_IDX: platform_idx},
                    config,
                )
                load_coroutines.append(load_coroutine)

    if refresh_coroutines:
        await asyncio.gather(*(create_eager_task(coro) for coro in refresh_coroutines))

    if load_coroutines:
        await asyncio.gather(*(create_eager_task(coro) for coro in load_coroutines))

    return True


async def async_get_config_and_coordinator(
    menuai: menuai, platform_domain: str, discovery_info: DiscoveryInfoType
) -> tuple[ConfigType, DataUpdateCoordinator[None], RestData]:
    """Get the config and coordinator for the platform from discovery."""
    shared_data = menuai.data[DOMAIN][REST_DATA][discovery_info[REST_IDX]]
    conf: ConfigType = menuai.data[DOMAIN][platform_domain][discovery_info[PLATFORM_IDX]]
    coordinator: DataUpdateCoordinator[None] = shared_data[COORDINATOR]
    rest: RestData = shared_data[REST]
    if rest.data is None:
        await coordinator.async_request_refresh()
    return conf, coordinator, rest


def _rest_coordinator(
    menuai: menuai,
    rest: RestData,
    resource_template: template.Template | None,
    payload_template: template.Template | None,
    update_interval: timedelta,
) -> DataUpdateCoordinator[None]:
    """Wrap a DataUpdateCoordinator around the rest object."""
    if resource_template or payload_template:

        async def _async_refresh_with_templates() -> None:
            if resource_template:
                rest.set_url(resource_template.async_render(parse_result=False))
            if payload_template:
                rest.set_payload(payload_template.async_render(parse_result=False))
            await rest.async_update()

        update_method = _async_refresh_with_templates
    else:
        update_method = rest.async_update

    return DataUpdateCoordinator(
        menuai,
        _LOGGER,
        config_entry=None,
        name="rest data",
        update_method=update_method,
        update_interval=update_interval,
    )


def create_rest_data_from_config(menuai: menuai, config: ConfigType) -> RestData:
    """Create RestData from config."""
    resource: str | None = config.get(CONF_RESOURCE)
    resource_template: template.Template | None = config.get(CONF_RESOURCE_TEMPLATE)
    method: str = config[CONF_METHOD]
    payload: str | None = config.get(CONF_PAYLOAD)
    payload_template: template.Template | None = config.get(CONF_PAYLOAD_TEMPLATE)
    verify_ssl: bool = config[CONF_VERIFY_SSL]
    ssl_cipher_list: str = config.get(CONF_SSL_CIPHER_LIST, DEFAULT_SSL_CIPHER_LIST)
    username: str | None = config.get(CONF_USERNAME)
    password: str | None = config.get(CONF_PASSWORD)
    headers: dict[str, str] | None = config.get(CONF_HEADERS)
    params: dict[str, str] | None = config.get(CONF_PARAMS)
    timeout: int = config[CONF_TIMEOUT]
    encoding: str = config[CONF_ENCODING]
    if resource_template is not None:
        resource = resource_template.async_render(parse_result=False)

    if payload_template is not None:
        payload = payload_template.async_render(parse_result=False)

    if not resource:
        raise menuaiError("Resource not set for RestData")

    auth: httpx.DigestAuth | tuple[str, str] | None = None
    if username and password:
        if config.get(CONF_AUTHENTICATION) == HTTP_DIGEST_AUTHENTICATION:
            auth = httpx.DigestAuth(username, password)
        else:
            auth = (username, password)

    return RestData(
        menuai,
        method,
        resource,
        encoding,
        auth,
        headers,
        params,
        payload,
        verify_ssl,
        ssl_cipher_list,
        timeout,
    )
