"""Config flow tests for the Telegram Bot integration."""

from unittest.mock import patch

from telegram import ChatFullInfo, User
from telegram.constants import AccentColor
from telegram.error import BadRequest, InvalidToken, NetworkError

from menuai.components.telegram_bot.const import (
    ATTR_PARSER,
    BOT_NAME,
    CONF_ALLOWED_CHAT_IDS,
    CONF_BOT_COUNT,
    CONF_CHAT_ID,
    CONF_PROXY_URL,
    CONF_TRUSTED_NETWORKS,
    DOMAIN,
    ERROR_FIELD,
    ERROR_MESSAGE,
    ISSUE_DEPRECATED_YAML,
    ISSUE_DEPRECATED_YAML_IMPORT_ISSUE_ERROR,
    PARSER_HTML,
    PARSER_MD,
    PLATFORM_BROADCAST,
    PLATFORM_WEBHOOKS,
    SUBENTRY_TYPE_ALLOWED_CHAT_IDS,
)
from menuai.config_entries import SOURCE_IMPORT, SOURCE_USER, ConfigSubentry
from menuai.const import CONF_API_KEY, CONF_PLATFORM, CONF_URL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.issue_registry import IssueRegistry

from tests.common import MockConfigEntry


async def test_options_flow(
    menuai: menuai, mock_webhooks_config_entry: MockConfigEntry
) -> None:
    """Test options flow."""

    mock_webhooks_config_entry.add_to_menuai(menuai)

    # test: no input

    result = await menuai.config_entries.options.async_init(
        mock_webhooks_config_entry.entry_id
    )
    await menuai.async_block_till_done()

    assert result["step_id"] == "init"
    assert result["type"] == FlowResultType.FORM

    # test: valid input

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {
            ATTR_PARSER: PARSER_HTML,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][ATTR_PARSER] == PARSER_HTML


async def test_reconfigure_flow_broadcast(
    menuai: menuai,
    mock_webhooks_config_entry: MockConfigEntry,
    mock_external_calls: None,
) -> None:
    """Test reconfigure flow for broadcast bot."""
    mock_webhooks_config_entry.add_to_menuai(menuai)

    result = await mock_webhooks_config_entry.start_reconfigure_flow(menuai)
    assert result["step_id"] == "reconfigure"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    # test: invalid proxy url

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me",
    ) as mock_bot:
        mock_bot.side_effect = NetworkError("mock invalid proxy")

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_PLATFORM: PLATFORM_BROADCAST,
                CONF_PROXY_URL: "invalid",
            },
        )
        await menuai.async_block_till_done()

    assert result["step_id"] == "reconfigure"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_proxy_url"

    # test: valid

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PLATFORM: PLATFORM_BROADCAST,
            CONF_PROXY_URL: "https://test",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_webhooks_config_entry.data[CONF_PLATFORM] == PLATFORM_BROADCAST


async def test_reconfigure_flow_webhooks(
    menuai: menuai,
    mock_webhooks_config_entry: MockConfigEntry,
    mock_external_calls: None,
) -> None:
    """Test reconfigure flow for webhook."""
    mock_webhooks_config_entry.add_to_menuai(menuai)

    result = await mock_webhooks_config_entry.start_reconfigure_flow(menuai)
    assert result["step_id"] == "reconfigure"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PLATFORM: PLATFORM_WEBHOOKS,
            CONF_PROXY_URL: "https://test",
        },
    )
    await menuai.async_block_till_done()

    assert result["step_id"] == "webhooks"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    # test: invalid url

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: "http://test",
            CONF_TRUSTED_NETWORKS: "149.154.160.0/20,91.108.4.0/22",
        },
    )

    assert result["step_id"] == "webhooks"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_url"

    # test: HA external url not configured

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TRUSTED_NETWORKS: "149.154.160.0/20,91.108.4.0/22"},
    )

    assert result["step_id"] == "webhooks"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "no_url_available"

    # test: invalid trusted networks

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: "https://reconfigure",
            CONF_TRUSTED_NETWORKS: "invalid trusted networks",
        },
    )

    assert result["step_id"] == "webhooks"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_trusted_networks"

    # test: valid input

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: "https://reconfigure",
            CONF_TRUSTED_NETWORKS: "149.154.160.0/20",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_webhooks_config_entry.data[CONF_URL] == "https://reconfigure"
    assert mock_webhooks_config_entry.data[CONF_TRUSTED_NETWORKS] == [
        "149.154.160.0/20"
    ]


async def test_create_entry(
    menuai: menuai,
) -> None:
    """Test user flow."""

    # test: no input

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    # test: invalid proxy url

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me",
    ) as mock_bot:
        mock_bot.side_effect = NetworkError("mock invalid proxy")

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_PLATFORM: PLATFORM_WEBHOOKS,
                CONF_API_KEY: "mock api key",
                CONF_PROXY_URL: "invalid",
            },
        )
        await menuai.async_block_till_done()

    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_proxy_url"

    # test: valid input, to continue with webhooks step

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me",
        return_value=User(123456, "Testbot", True),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_PLATFORM: PLATFORM_WEBHOOKS,
                CONF_API_KEY: "mock api key",
                CONF_PROXY_URL: "https://proxy",
            },
        )
        await menuai.async_block_till_done()

    assert result["step_id"] == "webhooks"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    # test: valid input for webhooks

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: "https://test",
            CONF_TRUSTED_NETWORKS: "149.154.160.0/20",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Testbot"
    assert result["data"][CONF_PLATFORM] == PLATFORM_WEBHOOKS
    assert result["data"][CONF_API_KEY] == "mock api key"
    assert result["data"][CONF_PROXY_URL] == "https://proxy"
    assert result["data"][CONF_URL] == "https://test"
    assert result["data"][CONF_TRUSTED_NETWORKS] == ["149.154.160.0/20"]


async def test_reauth_flow(
    menuai: menuai, mock_webhooks_config_entry: MockConfigEntry
) -> None:
    """Test a reauthentication flow."""
    mock_webhooks_config_entry.add_to_menuai(menuai)

    result = await mock_webhooks_config_entry.start_reauth_flow(
        menuai, data={CONF_API_KEY: "dummy"}
    )
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    # test: reauth invalid api key

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me"
    ) as mock_bot:
        mock_bot.side_effect = InvalidToken("mock invalid token error")

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "new mock api key"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_api_key"

    # test: valid

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me",
        return_value=User(123456, "Testbot", True),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "new mock api key"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_webhooks_config_entry.data[CONF_API_KEY] == "new mock api key"


async def test_subentry_flow(
    menuai: menuai, mock_broadcast_config_entry: MockConfigEntry
) -> None:
    """Test subentry flow."""
    mock_broadcast_config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me",
        return_value=User(123456, "Testbot", True),
    ):
        assert await menuai.config_entries.async_setup(
            mock_broadcast_config_entry.entry_id
        )
        await menuai.async_block_till_done()

    result = await menuai.config_entries.subentries.async_init(
        (mock_broadcast_config_entry.entry_id, SUBENTRY_TYPE_ALLOWED_CHAT_IDS),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_chat",
        return_value=ChatFullInfo(
            id=987654321,
            title="mock title",
            first_name="mock first_name",
            type="PRIVATE",
            max_reaction_count=100,
            accent_color_id=AccentColor.COLOR_000,
        ),
    ):
        result = await menuai.config_entries.subentries.async_configure(
            result["flow_id"],
            user_input={CONF_CHAT_ID: 987654321},
        )
        await menuai.async_block_till_done()

    subentry_id = list(mock_broadcast_config_entry.subentries)[-1]
    subentry: ConfigSubentry = mock_broadcast_config_entry.subentries[subentry_id]

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert subentry.subentry_type == SUBENTRY_TYPE_ALLOWED_CHAT_IDS
    assert subentry.title == "mock title"
    assert subentry.unique_id == "987654321"
    assert subentry.data == {CONF_CHAT_ID: 987654321}


async def test_subentry_flow_chat_error(
    menuai: menuai, mock_broadcast_config_entry: MockConfigEntry
) -> None:
    """Test subentry flow."""
    mock_broadcast_config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me",
        return_value=User(123456, "Testbot", True),
    ):
        assert await menuai.config_entries.async_setup(
            mock_broadcast_config_entry.entry_id
        )
        await menuai.async_block_till_done()

    result = await menuai.config_entries.subentries.async_init(
        (mock_broadcast_config_entry.entry_id, SUBENTRY_TYPE_ALLOWED_CHAT_IDS),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # test: chat not found

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_chat"
    ) as mock_bot:
        mock_bot.side_effect = BadRequest("mock chat not found")

        result = await menuai.config_entries.subentries.async_configure(
            result["flow_id"],
            user_input={CONF_CHAT_ID: 1234567890},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "chat_not_found"

    # test: chat id already configured

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_chat",
        return_value=ChatFullInfo(
            id=1234567890,
            title="mock title",
            first_name="mock first_name",
            type="PRIVATE",
            max_reaction_count=100,
            accent_color_id=AccentColor.COLOR_000,
        ),
    ):
        result = await menuai.config_entries.subentries.async_configure(
            result["flow_id"],
            user_input={CONF_CHAT_ID: 1234567890},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_failed(
    menuai: menuai, issue_registry: IssueRegistry
) -> None:
    """Test import flow failed."""

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me"
    ) as mock_bot:
        mock_bot.side_effect = InvalidToken("mock invalid token error")

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_PLATFORM: PLATFORM_BROADCAST,
                CONF_API_KEY: "mock api key",
                CONF_TRUSTED_NETWORKS: ["149.154.160.0/20"],
                CONF_BOT_COUNT: 1,
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "import_failed"

    issue = issue_registry.async_get_issue(
        domain=DOMAIN,
        issue_id=ISSUE_DEPRECATED_YAML,
    )
    assert issue.translation_key == ISSUE_DEPRECATED_YAML_IMPORT_ISSUE_ERROR
    assert (
        issue.translation_placeholders[BOT_NAME] == f"{PLATFORM_BROADCAST} Telegram bot"
    )
    assert issue.translation_placeholders[ERROR_FIELD] == "API key"
    assert issue.translation_placeholders[ERROR_MESSAGE] == "mock invalid token error"


async def test_import_multiple(
    menuai: menuai, issue_registry: IssueRegistry
) -> None:
    """Test import flow with multiple duplicated entries."""

    data = {
        CONF_PLATFORM: PLATFORM_BROADCAST,
        CONF_API_KEY: "mock api key",
        CONF_TRUSTED_NETWORKS: ["149.154.160.0/20"],
        CONF_ALLOWED_CHAT_IDS: [3334445550],
        CONF_BOT_COUNT: 2,
    }

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me",
        return_value=User(123456, "Testbot", True),
    ):
        # test: import first entry success

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=data,
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_PLATFORM] == PLATFORM_BROADCAST
        assert result["data"][CONF_API_KEY] == "mock api key"
        assert result["options"][ATTR_PARSER] == PARSER_MD

        issue = issue_registry.async_get_issue(
            domain=DOMAIN,
            issue_id=ISSUE_DEPRECATED_YAML,
        )
        assert (
            issue.translation_key == "deprecated_yaml_import_issue_has_more_platforms"
        )

        # test: import 2nd entry failed due to duplicate

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=data,
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_duplicate_entry(menuai: menuai) -> None:
    """Test user flow with duplicated entries."""

    data = {
        CONF_PLATFORM: PLATFORM_BROADCAST,
        CONF_API_KEY: "mock api key",
    }

    with patch(
        "menuai.components.telegram_bot.config_flow.Bot.get_me",
        return_value=User(123456, "Testbot", True),
    ):
        # test: import first entry success

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=data,
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_PLATFORM] == PLATFORM_BROADCAST
        assert result["data"][CONF_API_KEY] == "mock api key"
        assert result["options"][ATTR_PARSER] == PARSER_MD

        # test: import 2nd entry failed due to duplicate

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data=data,
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"
