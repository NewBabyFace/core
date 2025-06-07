"""Support for setting the level of logging for components."""

from __future__ import annotations

import logging
import re

import voluptuous as vol

from menuai.const import EVENT_LOGGING_CHANGED  # noqa: F401
from menuai.core import menuai, ServiceCall, callback
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from . import websocket_api
from .const import (
    ATTR_LEVEL,
    DOMAIN,
    LOGGER_DEFAULT,
    LOGGER_FILTERS,
    LOGGER_LOGS,
    LOGSEVERITY,
    SERVICE_SET_DEFAULT_LEVEL,
    SERVICE_SET_LEVEL,
)
from .helpers import (
    DATA_LOGGER,
    LoggerDomainConfig,
    LoggerSettings,
    _clear_logger_overwrites,  # noqa: F401
    set_default_log_level,
    set_log_levels,
)

_VALID_LOG_LEVEL = vol.All(vol.Upper, vol.In(LOGSEVERITY), LOGSEVERITY.__getitem__)

SERVICE_SET_DEFAULT_LEVEL_SCHEMA = vol.Schema({ATTR_LEVEL: _VALID_LOG_LEVEL})
SERVICE_SET_LEVEL_SCHEMA = vol.Schema({cv.string: _VALID_LOG_LEVEL})

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(LOGGER_DEFAULT): _VALID_LOG_LEVEL,
                vol.Optional(LOGGER_LOGS): vol.Schema({cv.string: _VALID_LOG_LEVEL}),
                vol.Optional(LOGGER_FILTERS): vol.Schema({cv.string: [cv.is_regex]}),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the logger component."""

    settings = LoggerSettings(menuai, config)

    domain_config = menuai.data[DATA_LOGGER] = LoggerDomainConfig({}, settings)
    logging.setLoggerClass(_get_logger_class(domain_config.overrides))

    websocket_api.async_load_websocket_api(menuai)

    await settings.async_load()

    # Set default log severity and filter
    logger_config = config.get(DOMAIN, {})

    if LOGGER_DEFAULT in logger_config:
        set_default_log_level(menuai, logger_config[LOGGER_DEFAULT])

    if LOGGER_FILTERS in logger_config:
        log_filters: dict[str, list[re.Pattern]] = logger_config[LOGGER_FILTERS]
        for key, value in log_filters.items():
            _add_log_filter(logging.getLogger(key), value)

    # Combine log levels configured in configuration.yaml with log levels set by frontend
    combined_logs = await settings.async_get_levels(menuai)
    set_log_levels(menuai, combined_logs)

    @callback
    def async_service_handler(service: ServiceCall) -> None:
        """Handle logger services."""
        if service.service == SERVICE_SET_DEFAULT_LEVEL:
            set_default_log_level(menuai, service.data[ATTR_LEVEL])
        else:
            set_log_levels(menuai, service.data)

    menuai.services.async_register(
        DOMAIN,
        SERVICE_SET_DEFAULT_LEVEL,
        async_service_handler,
        schema=SERVICE_SET_DEFAULT_LEVEL_SCHEMA,
    )

    menuai.services.async_register(
        DOMAIN,
        SERVICE_SET_LEVEL,
        async_service_handler,
        schema=SERVICE_SET_LEVEL_SCHEMA,
    )

    return True


def _add_log_filter(logger: logging.Logger, patterns: list[re.Pattern]) -> None:
    """Add a Filter to the logger based on a regexp of the filter_str."""

    def filter_func(logrecord: logging.LogRecord) -> bool:
        return not any(p.search(logrecord.getMessage()) for p in patterns)

    logger.addFilter(filter_func)


def _get_logger_class(menuai_overrides: dict[str, int]) -> type[logging.Logger]:
    """Create a logger subclass.

    logging.setLoggerClass checks if it is a subclass of Logger and
    so we cannot use partial to inject menuai_overrides.
    """

    class menuaiLogger(logging.Logger):
        """MenuAI aware logger class."""

        def setLevel(self, level: int | str) -> None:
            """Set the log level unless overridden."""
            if self.name in menuai_overrides:
                return

            super().setLevel(level)

        def orig_setLevel(self, level: int | str) -> None:
            """Set the log level."""
            super().setLevel(level)

    return menuaiLogger
