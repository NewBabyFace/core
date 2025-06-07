"""Test the OpenAI Conversation config flow."""

from unittest.mock import AsyncMock, patch

import httpx
from openai import APIConnectionError, AuthenticationError, BadRequestError
from openai.types.responses import Response, ResponseOutputMessage, ResponseOutputText
import pytest

from menuai import config_entries
from menuai.components.openai_conversation.config_flow import RECOMMENDED_OPTIONS
from menuai.components.openai_conversation.const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_REASONING_EFFORT,
    CONF_RECOMMENDED,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_WEB_SEARCH,
    CONF_WEB_SEARCH_CITY,
    CONF_WEB_SEARCH_CONTEXT_SIZE,
    CONF_WEB_SEARCH_COUNTRY,
    CONF_WEB_SEARCH_REGION,
    CONF_WEB_SEARCH_TIMEZONE,
    CONF_WEB_SEARCH_USER_LOCATION,
    DOMAIN,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_REASONING_EFFORT,
    RECOMMENDED_TOP_P,
)
from menuai.const import CONF_LLM_menuai_API
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    # Pretend we already set up a config entry.
    menuai.config.components.add("openai_conversation")
    MockConfigEntry(
        domain=DOMAIN,
        state=config_entries.ConfigEntryState.LOADED,
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "menuai.components.openai_conversation.config_flow.openai.resources.models.AsyncModels.list",
        ),
        patch(
            "menuai.components.openai_conversation.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "api_key": "bla",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        "api_key": "bla",
    }
    assert result2["options"] == RECOMMENDED_OPTIONS
    assert len(mock_setup_entry.mock_calls) == 1


async def test_options(
    menuai: menuai, mock_config_entry, mock_init_component
) -> None:
    """Test the options form."""
    options_flow = await menuai.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    options = await menuai.config_entries.options.async_configure(
        options_flow["flow_id"],
        {
            "prompt": "Speak like a pirate",
            "max_tokens": 200,
        },
    )
    await menuai.async_block_till_done()
    assert options["type"] is FlowResultType.CREATE_ENTRY
    assert options["data"]["prompt"] == "Speak like a pirate"
    assert options["data"]["max_tokens"] == 200
    assert options["data"][CONF_CHAT_MODEL] == RECOMMENDED_CHAT_MODEL


async def test_options_unsupported_model(
    menuai: menuai, mock_config_entry, mock_init_component
) -> None:
    """Test the options form giving error about models not supported."""
    options_flow = await menuai.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    result = await menuai.config_entries.options.async_configure(
        options_flow["flow_id"],
        {
            CONF_RECOMMENDED: False,
            CONF_PROMPT: "Speak like a pirate",
            CONF_CHAT_MODEL: "o1-mini",
            CONF_LLM_menuai_API: ["assist"],
        },
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"chat_model": "model_not_supported"}


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (APIConnectionError(request=None), "cannot_connect"),
        (
            AuthenticationError(
                response=httpx.Response(status_code=None, request=""),
                body=None,
                message=None,
            ),
            "invalid_auth",
        ),
        (
            BadRequestError(
                response=httpx.Response(status_code=None, request=""),
                body=None,
                message=None,
            ),
            "unknown",
        ),
    ],
)
async def test_form_invalid_auth(menuai: menuai, side_effect, error) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.openai_conversation.config_flow.openai.resources.models.AsyncModels.list",
        side_effect=side_effect,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "api_key": "bla",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": error}


@pytest.mark.parametrize(
    ("current_options", "new_options", "expected_options"),
    [
        (
            {
                CONF_RECOMMENDED: True,
                CONF_PROMPT: "bla",
            },
            {
                CONF_RECOMMENDED: False,
                CONF_PROMPT: "Speak like a pirate",
                CONF_TEMPERATURE: 0.3,
            },
            {
                CONF_RECOMMENDED: False,
                CONF_PROMPT: "Speak like a pirate",
                CONF_TEMPERATURE: 0.3,
                CONF_CHAT_MODEL: RECOMMENDED_CHAT_MODEL,
                CONF_TOP_P: RECOMMENDED_TOP_P,
                CONF_MAX_TOKENS: RECOMMENDED_MAX_TOKENS,
                CONF_REASONING_EFFORT: RECOMMENDED_REASONING_EFFORT,
                CONF_WEB_SEARCH: False,
                CONF_WEB_SEARCH_CONTEXT_SIZE: "medium",
                CONF_WEB_SEARCH_USER_LOCATION: False,
            },
        ),
        (
            {
                CONF_RECOMMENDED: False,
                CONF_PROMPT: "Speak like a pirate",
                CONF_TEMPERATURE: 0.3,
                CONF_CHAT_MODEL: RECOMMENDED_CHAT_MODEL,
                CONF_TOP_P: RECOMMENDED_TOP_P,
                CONF_MAX_TOKENS: RECOMMENDED_MAX_TOKENS,
                CONF_REASONING_EFFORT: RECOMMENDED_REASONING_EFFORT,
                CONF_WEB_SEARCH: False,
                CONF_WEB_SEARCH_CONTEXT_SIZE: "medium",
                CONF_WEB_SEARCH_USER_LOCATION: False,
            },
            {
                CONF_RECOMMENDED: True,
                CONF_LLM_menuai_API: ["assist"],
                CONF_PROMPT: "",
            },
            {
                CONF_RECOMMENDED: True,
                CONF_LLM_menuai_API: ["assist"],
                CONF_PROMPT: "",
            },
        ),
        (
            {
                CONF_RECOMMENDED: True,
                CONF_LLM_menuai_API: "assist",
                CONF_PROMPT: "",
            },
            {
                CONF_RECOMMENDED: True,
                CONF_LLM_menuai_API: ["assist"],
                CONF_PROMPT: "",
            },
            {
                CONF_RECOMMENDED: True,
                CONF_LLM_menuai_API: ["assist"],
                CONF_PROMPT: "",
            },
        ),
    ],
)
async def test_options_switching(
    menuai: menuai,
    mock_config_entry,
    mock_init_component,
    current_options,
    new_options,
    expected_options,
) -> None:
    """Test the options form."""
    menuai.config_entries.async_update_entry(mock_config_entry, options=current_options)
    options_flow = await menuai.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    if current_options.get(CONF_RECOMMENDED) != new_options.get(CONF_RECOMMENDED):
        options_flow = await menuai.config_entries.options.async_configure(
            options_flow["flow_id"],
            {
                **current_options,
                CONF_RECOMMENDED: new_options[CONF_RECOMMENDED],
            },
        )
    options = await menuai.config_entries.options.async_configure(
        options_flow["flow_id"],
        new_options,
    )
    await menuai.async_block_till_done()
    assert options["type"] is FlowResultType.CREATE_ENTRY
    assert options["data"] == expected_options


async def test_options_web_search_user_location(
    menuai: menuai, mock_config_entry, mock_init_component
) -> None:
    """Test fetching user location."""
    options_flow = await menuai.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    menuai.config.country = "US"
    menuai.config.time_zone = "America/Los_Angeles"
    menuai.states.async_set(
        "zone.home", "0", {"latitude": 37.7749, "longitude": -122.4194}
    )
    with patch(
        "openai.resources.responses.AsyncResponses.create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = Response(
            object="response",
            id="resp_A",
            created_at=1700000000,
            model="gpt-4o-mini",
            parallel_tool_calls=True,
            tool_choice="auto",
            tools=[],
            output=[
                ResponseOutputMessage(
                    type="message",
                    id="msg_A",
                    content=[
                        ResponseOutputText(
                            type="output_text",
                            text='{"city": "San Francisco", "region": "California"}',
                            annotations=[],
                        )
                    ],
                    role="assistant",
                    status="completed",
                )
            ],
        )

        options = await menuai.config_entries.options.async_configure(
            options_flow["flow_id"],
            {
                CONF_RECOMMENDED: False,
                CONF_PROMPT: "Speak like a pirate",
                CONF_TEMPERATURE: 1.0,
                CONF_CHAT_MODEL: RECOMMENDED_CHAT_MODEL,
                CONF_TOP_P: RECOMMENDED_TOP_P,
                CONF_MAX_TOKENS: RECOMMENDED_MAX_TOKENS,
                CONF_REASONING_EFFORT: RECOMMENDED_REASONING_EFFORT,
                CONF_WEB_SEARCH: True,
                CONF_WEB_SEARCH_CONTEXT_SIZE: "medium",
                CONF_WEB_SEARCH_USER_LOCATION: True,
            },
        )
        await menuai.async_block_till_done()
    assert (
        mock_create.call_args.kwargs["input"][0]["content"] == "Where are the following"
        " coordinates located: (37.7749, -122.4194)?"
    )
    assert options["type"] is FlowResultType.CREATE_ENTRY
    assert options["data"] == {
        CONF_RECOMMENDED: False,
        CONF_PROMPT: "Speak like a pirate",
        CONF_TEMPERATURE: 1.0,
        CONF_CHAT_MODEL: RECOMMENDED_CHAT_MODEL,
        CONF_TOP_P: RECOMMENDED_TOP_P,
        CONF_MAX_TOKENS: RECOMMENDED_MAX_TOKENS,
        CONF_REASONING_EFFORT: RECOMMENDED_REASONING_EFFORT,
        CONF_WEB_SEARCH: True,
        CONF_WEB_SEARCH_CONTEXT_SIZE: "medium",
        CONF_WEB_SEARCH_USER_LOCATION: True,
        CONF_WEB_SEARCH_CITY: "San Francisco",
        CONF_WEB_SEARCH_REGION: "California",
        CONF_WEB_SEARCH_COUNTRY: "US",
        CONF_WEB_SEARCH_TIMEZONE: "America/Los_Angeles",
    }


async def test_options_web_search_unsupported_model(
    menuai: menuai, mock_config_entry, mock_init_component
) -> None:
    """Test the options form giving error about web search not being available."""
    options_flow = await menuai.config_entries.options.async_init(
        mock_config_entry.entry_id
    )
    result = await menuai.config_entries.options.async_configure(
        options_flow["flow_id"],
        {
            CONF_RECOMMENDED: False,
            CONF_PROMPT: "Speak like a pirate",
            CONF_CHAT_MODEL: "o1-pro",
            CONF_LLM_menuai_API: ["assist"],
            CONF_WEB_SEARCH: True,
        },
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"web_search": "web_search_not_supported"}
