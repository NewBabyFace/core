"""Test the sentry config flow."""

import logging
from unittest.mock import patch

from sentry_sdk.utils import BadDsn

from menuai.components.sentry.const import (
    CONF_ENVIRONMENT,
    CONF_EVENT_CUSTOM_COMPONENTS,
    CONF_EVENT_HANDLED,
    CONF_EVENT_THIRD_PARTY_PACKAGES,
    CONF_LOGGING_EVENT_LEVEL,
    CONF_LOGGING_LEVEL,
    CONF_TRACING,
    CONF_TRACING_SAMPLE_RATE,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_user_flow_implementation(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {}

    with (
        patch("menuai.components.sentry.config_flow.Dsn"),
        patch(
            "menuai.components.sentry.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"dsn": "http://public@sentry.local/1"},
        )

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "Sentry"
    assert result2.get("data") == {
        "dsn": "http://public@sentry.local/1",
    }
    await menuai.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 1


async def test_integration_already_exists(menuai: menuai) -> None:
    """Test we only allow a single config flow."""
    MockConfigEntry(domain=DOMAIN).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "single_instance_allowed"


async def test_user_flow_bad_dsn(menuai: menuai) -> None:
    """Test we handle bad dsn error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "menuai.components.sentry.config_flow.Dsn",
        side_effect=BadDsn,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"dsn": "foo"},
        )

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("errors") == {"base": "bad_dsn"}


async def test_user_flow_unknown_exception(menuai: menuai) -> None:
    """Test we handle any unknown exception error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "menuai.components.sentry.config_flow.Dsn",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"dsn": "foo"},
        )

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("errors") == {"base": "unknown"}


async def test_options_flow(menuai: menuai) -> None:
    """Test options config flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"dsn": "http://public@sentry.local/1"},
    )
    entry.add_to_menuai(menuai)

    with patch("menuai.components.sentry.async_setup_entry", return_value=True):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_ENVIRONMENT: "Test",
            CONF_EVENT_CUSTOM_COMPONENTS: True,
            CONF_EVENT_HANDLED: True,
            CONF_EVENT_THIRD_PARTY_PACKAGES: True,
            CONF_LOGGING_EVENT_LEVEL: logging.DEBUG,
            CONF_LOGGING_LEVEL: logging.DEBUG,
            CONF_TRACING: True,
            CONF_TRACING_SAMPLE_RATE: 0.5,
        },
    )

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("data") == {
        CONF_ENVIRONMENT: "Test",
        CONF_EVENT_CUSTOM_COMPONENTS: True,
        CONF_EVENT_HANDLED: True,
        CONF_EVENT_THIRD_PARTY_PACKAGES: True,
        CONF_LOGGING_EVENT_LEVEL: logging.DEBUG,
        CONF_LOGGING_LEVEL: logging.DEBUG,
        CONF_TRACING: True,
        CONF_TRACING_SAMPLE_RATE: 0.5,
    }
