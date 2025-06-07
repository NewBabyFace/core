"""Config flow for Anthropic integration."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
import logging
from types import MappingProxyType
from typing import Any

import anthropic
import voluptuous as vol

from menuai.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from menuai.const import CONF_API_KEY, CONF_LLM_menuai_API
from menuai.core import menuai
from menuai.helpers import llm
from menuai.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TemplateSelector,
)

from .const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_RECOMMENDED,
    CONF_TEMPERATURE,
    CONF_THINKING_BUDGET,
    DOMAIN,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_THINKING_BUDGET,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)

RECOMMENDED_OPTIONS = {
    CONF_RECOMMENDED: True,
    CONF_LLM_menuai_API: [llm.LLM_API_ASSIST],
    CONF_PROMPT: llm.DEFAULT_INSTRUCTIONS_PROMPT,
}


async def validate_input(menuai: menuai, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    client = await menuai.async_add_executor_job(
        partial(anthropic.AsyncAnthropic, api_key=data[CONF_API_KEY])
    )
    await client.models.list(timeout=10.0)


class AnthropicConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Anthropic."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                await validate_input(self.menuai, user_input)
            except anthropic.APITimeoutError:
                errors["base"] = "timeout_connect"
            except anthropic.APIConnectionError:
                errors["base"] = "cannot_connect"
            except anthropic.APIStatusError as e:
                errors["base"] = "unknown"
                if (
                    isinstance(e.body, dict)
                    and (error := e.body.get("error"))
                    and error.get("type") == "authentication_error"
                ):
                    errors["base"] = "authentication_error"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Claude",
                    data=user_input,
                    options=RECOMMENDED_OPTIONS,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors or None
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return AnthropicOptionsFlow(config_entry)


class AnthropicOptionsFlow(OptionsFlow):
    """Anthropic config flow options handler."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.last_rendered_recommended = config_entry.options.get(
            CONF_RECOMMENDED, False
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        options: dict[str, Any] | MappingProxyType[str, Any] = self.config_entry.options
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input[CONF_RECOMMENDED] == self.last_rendered_recommended:
                if not user_input.get(CONF_LLM_menuai_API):
                    user_input.pop(CONF_LLM_menuai_API, None)
                if user_input.get(
                    CONF_THINKING_BUDGET, RECOMMENDED_THINKING_BUDGET
                ) >= user_input.get(CONF_MAX_TOKENS, RECOMMENDED_MAX_TOKENS):
                    errors[CONF_THINKING_BUDGET] = "thinking_budget_too_large"

                if not errors:
                    return self.async_create_entry(title="", data=user_input)
            else:
                # Re-render the options again, now with the recommended options shown/hidden
                self.last_rendered_recommended = user_input[CONF_RECOMMENDED]

                options = {
                    CONF_RECOMMENDED: user_input[CONF_RECOMMENDED],
                    CONF_PROMPT: user_input[CONF_PROMPT],
                    CONF_LLM_menuai_API: user_input.get(CONF_LLM_menuai_API),
                }

        suggested_values = options.copy()
        if not suggested_values.get(CONF_PROMPT):
            suggested_values[CONF_PROMPT] = llm.DEFAULT_INSTRUCTIONS_PROMPT
        if (
            suggested_llm_apis := suggested_values.get(CONF_LLM_menuai_API)
        ) and isinstance(suggested_llm_apis, str):
            suggested_values[CONF_LLM_menuai_API] = [suggested_llm_apis]

        schema = self.add_suggested_values_to_schema(
            vol.Schema(anthropic_config_option_schema(self.menuai, options)),
            suggested_values,
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors or None,
        )


def anthropic_config_option_schema(
    menuai: menuai,
    options: Mapping[str, Any],
) -> dict:
    """Return a schema for Anthropic completion options."""
    menuai_apis: list[SelectOptionDict] = [
        SelectOptionDict(
            label=api.name,
            value=api.id,
        )
        for api in llm.async_get_apis(menuai)
    ]

    schema = {
        vol.Optional(CONF_PROMPT): TemplateSelector(),
        vol.Optional(
            CONF_LLM_menuai_API,
        ): SelectSelector(SelectSelectorConfig(options=menuai_apis, multiple=True)),
        vol.Required(
            CONF_RECOMMENDED, default=options.get(CONF_RECOMMENDED, False)
        ): bool,
    }

    if options.get(CONF_RECOMMENDED):
        return schema

    schema.update(
        {
            vol.Optional(
                CONF_CHAT_MODEL,
                default=RECOMMENDED_CHAT_MODEL,
            ): str,
            vol.Optional(
                CONF_MAX_TOKENS,
                default=RECOMMENDED_MAX_TOKENS,
            ): int,
            vol.Optional(
                CONF_TEMPERATURE,
                default=RECOMMENDED_TEMPERATURE,
            ): NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05)),
            vol.Optional(
                CONF_THINKING_BUDGET,
                default=RECOMMENDED_THINKING_BUDGET,
            ): int,
        }
    )
    return schema
