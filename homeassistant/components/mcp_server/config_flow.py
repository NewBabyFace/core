"""Config flow for the Model Context Protocol Server integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from menuai.config_entries import ConfigFlow, ConfigFlowResult
from menuai.const import CONF_LLM_menuai_API
from menuai.helpers import llm
from menuai.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

MORE_INFO_URL = "https://www.home-assistant.io/integrations/mcp_server/#configuration"


class ModelContextServerProtocolConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Model Context Protocol Server."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        llm_apis = {api.id: api.name for api in llm.async_get_apis(self.menuai)}
        if user_input is not None:
            return self.async_create_entry(
                title=llm_apis[user_input[CONF_LLM_menuai_API]], data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_LLM_menuai_API,
                        default=llm.LLM_API_ASSIST,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    label=name,
                                    value=llm_api_id,
                                )
                                for llm_api_id, name in llm_apis.items()
                            ]
                        )
                    ),
                }
            ),
            description_placeholders={"more_info_url": MORE_INFO_URL},
        )
