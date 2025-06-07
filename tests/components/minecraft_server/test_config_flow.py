"""Tests for the Minecraft Server config flow."""

from unittest.mock import patch

from mcstatus import BedrockServer, JavaServer

from menuai.components.minecraft_server.api import MinecraftServerType
from menuai.components.minecraft_server.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_ADDRESS, CONF_TYPE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import (
    TEST_ADDRESS,
    TEST_BEDROCK_STATUS_RESPONSE,
    TEST_HOST,
    TEST_JAVA_STATUS_RESPONSE,
    TEST_PORT,
)

from tests.common import MockConfigEntry

USER_INPUT = {
    CONF_ADDRESS: TEST_ADDRESS,
}


async def test_full_flow_java(menuai: menuai) -> None:
    """Test config entry in case of a successful connection to a Java Edition server."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.lookup",
            side_effect=ValueError,
        ),
        patch(
            "menuai.components.minecraft_server.api.JavaServer.async_lookup",
            return_value=JavaServer(host=TEST_HOST, port=TEST_PORT),
        ),
        patch(
            "menuai.components.minecraft_server.api.JavaServer.async_status",
            return_value=TEST_JAVA_STATUS_RESPONSE,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == USER_INPUT[CONF_ADDRESS]
        assert result["data"][CONF_ADDRESS] == TEST_ADDRESS
        assert result["data"][CONF_TYPE] == MinecraftServerType.JAVA_EDITION


async def test_full_flow_bedrock(menuai: menuai) -> None:
    """Test config entry in case of a successful connection to a Bedrock Edition server."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.lookup",
            return_value=BedrockServer(host=TEST_HOST, port=TEST_PORT),
        ),
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.async_status",
            return_value=TEST_BEDROCK_STATUS_RESPONSE,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == USER_INPUT[CONF_ADDRESS]
        assert result["data"][CONF_ADDRESS] == TEST_ADDRESS
        assert result["data"][CONF_TYPE] == MinecraftServerType.BEDROCK_EDITION


async def test_service_already_configured_java(
    menuai: menuai, java_mock_config_entry: MockConfigEntry
) -> None:
    """Test config flow abort if a Java Edition server is already configured."""
    java_mock_config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.lookup",
            side_effect=ValueError,
        ),
        patch(
            "menuai.components.minecraft_server.api.JavaServer.async_lookup",
            return_value=JavaServer(host=TEST_HOST, port=TEST_PORT),
        ),
        patch(
            "menuai.components.minecraft_server.api.JavaServer.async_status",
            return_value=TEST_JAVA_STATUS_RESPONSE,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_service_already_configured_bedrock(
    menuai: menuai, bedrock_mock_config_entry: MockConfigEntry
) -> None:
    """Test config flow abort if a Bedrock Edition server is already configured."""
    bedrock_mock_config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.lookup",
            return_value=BedrockServer(host=TEST_HOST, port=TEST_PORT),
        ),
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.async_status",
            return_value=TEST_BEDROCK_STATUS_RESPONSE,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_recovery_java(menuai: menuai) -> None:
    """Test config flow recovery with a Java Edition server (successful connection after a failed connection)."""
    with (
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.lookup",
            side_effect=ValueError,
        ),
        patch(
            "menuai.components.minecraft_server.api.JavaServer.async_lookup",
            return_value=JavaServer(host=TEST_HOST, port=TEST_PORT),
        ),
        patch(
            "menuai.components.minecraft_server.api.JavaServer.async_status",
            side_effect=OSError,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}

    with (
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.lookup",
            side_effect=ValueError,
        ),
        patch(
            "menuai.components.minecraft_server.api.JavaServer.async_lookup",
            return_value=JavaServer(host=TEST_HOST, port=TEST_PORT),
        ),
        patch(
            "menuai.components.minecraft_server.api.JavaServer.async_status",
            return_value=TEST_JAVA_STATUS_RESPONSE,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            flow_id=result["flow_id"], user_input=USER_INPUT
        )
        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == USER_INPUT[CONF_ADDRESS]
        assert result2["data"][CONF_ADDRESS] == TEST_ADDRESS
        assert result2["data"][CONF_TYPE] == MinecraftServerType.JAVA_EDITION


async def test_recovery_bedrock(menuai: menuai) -> None:
    """Test config flow recovery with a Bedrock Edition server (successful connection after a failed connection)."""
    with (
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.lookup",
            return_value=BedrockServer(host=TEST_HOST, port=TEST_PORT),
        ),
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.async_status",
            side_effect=OSError,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}

    with (
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.lookup",
            return_value=BedrockServer(host=TEST_HOST, port=TEST_PORT),
        ),
        patch(
            "menuai.components.minecraft_server.api.BedrockServer.async_status",
            return_value=TEST_BEDROCK_STATUS_RESPONSE,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            flow_id=result["flow_id"], user_input=USER_INPUT
        )
        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == USER_INPUT[CONF_ADDRESS]
        assert result2["data"][CONF_ADDRESS] == TEST_ADDRESS
        assert result2["data"][CONF_TYPE] == MinecraftServerType.BEDROCK_EDITION
