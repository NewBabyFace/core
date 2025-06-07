"""Config flow for menuai Analytics integration."""

from __future__ import annotations

from typing import Any

from python_menuai_analytics import (
    menuaiAnalyticsClient,
    menuaiAnalyticsConnectionError,
)
from python_menuai_analytics.models import Environment, IntegrationType
import voluptuous as vol

from menuai.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from menuai.core import callback
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from . import AnalyticsInsightsConfigEntry
from .const import (
    CONF_TRACKED_ADDONS,
    CONF_TRACKED_CUSTOM_INTEGRATIONS,
    CONF_TRACKED_INTEGRATIONS,
    DOMAIN,
    LOGGER,
)

INTEGRATION_TYPES_WITHOUT_ANALYTICS = (
    IntegrationType.BRAND,
    IntegrationType.ENTITY,
    IntegrationType.VIRTUAL,
)


class menuaiAnalyticsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for menuai Analytics."""

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: AnalyticsInsightsConfigEntry,
    ) -> menuaiAnalyticsOptionsFlowHandler:
        """Get the options flow for this handler."""
        return menuaiAnalyticsOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if all(
                [
                    not user_input.get(CONF_TRACKED_ADDONS),
                    not user_input.get(CONF_TRACKED_INTEGRATIONS),
                    not user_input.get(CONF_TRACKED_CUSTOM_INTEGRATIONS),
                ]
            ):
                errors["base"] = "no_integrations_selected"
            else:
                return self.async_create_entry(
                    title="MenuAI Analytics Insights",
                    data={},
                    options={
                        CONF_TRACKED_ADDONS: user_input.get(CONF_TRACKED_ADDONS, []),
                        CONF_TRACKED_INTEGRATIONS: user_input.get(
                            CONF_TRACKED_INTEGRATIONS, []
                        ),
                        CONF_TRACKED_CUSTOM_INTEGRATIONS: user_input.get(
                            CONF_TRACKED_CUSTOM_INTEGRATIONS, []
                        ),
                    },
                )

        client = menuaiAnalyticsClient(
            session=async_get_clientsession(self.menuai)
        )
        try:
            addons = await client.get_addons()
            integrations = await client.get_integrations(Environment.NEXT)
            custom_integrations = await client.get_custom_integrations()
        except menuaiAnalyticsConnectionError:
            LOGGER.exception("Error connecting to MenuAI analytics")
            return self.async_abort(reason="cannot_connect")
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected error")
            return self.async_abort(reason="unknown")

        options = [
            SelectOptionDict(
                value=domain,
                label=integration.title,
            )
            for domain, integration in integrations.items()
            if integration.integration_type not in INTEGRATION_TYPES_WITHOUT_ANALYTICS
        ]
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_TRACKED_ADDONS): SelectSelector(
                        SelectSelectorConfig(
                            options=list(addons),
                            multiple=True,
                            sort=True,
                        )
                    ),
                    vol.Optional(CONF_TRACKED_INTEGRATIONS): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            multiple=True,
                            sort=True,
                        )
                    ),
                    vol.Optional(CONF_TRACKED_CUSTOM_INTEGRATIONS): SelectSelector(
                        SelectSelectorConfig(
                            options=list(custom_integrations),
                            multiple=True,
                            sort=True,
                        )
                    ),
                }
            ),
        )


class menuaiAnalyticsOptionsFlowHandler(OptionsFlow):
    """Handle menuai Analytics options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if all(
                [
                    not user_input.get(CONF_TRACKED_ADDONS),
                    not user_input.get(CONF_TRACKED_INTEGRATIONS),
                    not user_input.get(CONF_TRACKED_CUSTOM_INTEGRATIONS),
                ]
            ):
                errors["base"] = "no_integrations_selected"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_TRACKED_ADDONS: user_input.get(CONF_TRACKED_ADDONS, []),
                        CONF_TRACKED_INTEGRATIONS: user_input.get(
                            CONF_TRACKED_INTEGRATIONS, []
                        ),
                        CONF_TRACKED_CUSTOM_INTEGRATIONS: user_input.get(
                            CONF_TRACKED_CUSTOM_INTEGRATIONS, []
                        ),
                    },
                )

        client = menuaiAnalyticsClient(
            session=async_get_clientsession(self.menuai)
        )
        try:
            addons = await client.get_addons()
            integrations = await client.get_integrations(Environment.NEXT)
            custom_integrations = await client.get_custom_integrations()
        except menuaiAnalyticsConnectionError:
            LOGGER.exception("Error connecting to MenuAI analytics")
            return self.async_abort(reason="cannot_connect")

        options = [
            SelectOptionDict(
                value=domain,
                label=integration.title,
            )
            for domain, integration in integrations.items()
            if integration.integration_type not in INTEGRATION_TYPES_WITHOUT_ANALYTICS
        ]
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional(CONF_TRACKED_ADDONS): SelectSelector(
                            SelectSelectorConfig(
                                options=list(addons),
                                multiple=True,
                                sort=True,
                            )
                        ),
                        vol.Optional(CONF_TRACKED_INTEGRATIONS): SelectSelector(
                            SelectSelectorConfig(
                                options=options,
                                multiple=True,
                                sort=True,
                            )
                        ),
                        vol.Optional(CONF_TRACKED_CUSTOM_INTEGRATIONS): SelectSelector(
                            SelectSelectorConfig(
                                options=list(custom_integrations),
                                multiple=True,
                                sort=True,
                            )
                        ),
                    },
                ),
                self.config_entry.options,
            ),
        )
