"""Tests for the SleepIQ config flow."""

from unittest.mock import AsyncMock, patch

from asyncsleepiq import SleepIQLoginException, SleepIQTimeoutException
import pytest

from menuai import config_entries, setup
from menuai.components.sleepiq.const import DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import SLEEPIQ_CONFIG, setup_platform

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_import(menuai: menuai) -> None:
    """Test that we can import a config entry."""
    with patch("asyncsleepiq.AsyncSleepIQ.login"):
        assert await setup.async_setup_component(menuai, DOMAIN, {DOMAIN: SLEEPIQ_CONFIG})
        await menuai.async_block_till_done()

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert entry.data[CONF_USERNAME] == SLEEPIQ_CONFIG[CONF_USERNAME]
    assert entry.data[CONF_PASSWORD] == SLEEPIQ_CONFIG[CONF_PASSWORD]


@pytest.mark.parametrize(
    "side_effect", [SleepIQLoginException, SleepIQTimeoutException]
)
async def test_import_failure(menuai: menuai, side_effect) -> None:
    """Test that we won't import a config entry on login failure."""
    with patch(
        "asyncsleepiq.AsyncSleepIQ.login",
        side_effect=side_effect,
    ):
        assert await setup.async_setup_component(menuai, DOMAIN, {DOMAIN: SLEEPIQ_CONFIG})
        await menuai.async_block_till_done()

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 0


async def test_show_set_form(menuai: menuai) -> None:
    """Test that the setup form is served."""
    with patch("asyncsleepiq.AsyncSleepIQ.login"):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=None
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (SleepIQLoginException, "invalid_auth"),
        (SleepIQTimeoutException, "cannot_connect"),
    ],
)
async def test_login_failure(menuai: menuai, side_effect, error) -> None:
    """Test that we show user form with appropriate error on login failure."""
    with patch(
        "asyncsleepiq.AsyncSleepIQ.login",
        side_effect=side_effect,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=SLEEPIQ_CONFIG
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": error}


async def test_success(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test successful flow provides entry creation data."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch("asyncsleepiq.AsyncSleepIQ.login", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], SLEEPIQ_CONFIG
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_USERNAME] == SLEEPIQ_CONFIG[CONF_USERNAME]
    assert result2["data"][CONF_PASSWORD] == SLEEPIQ_CONFIG[CONF_PASSWORD]
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reauth_password(menuai: menuai) -> None:
    """Test reauth form."""

    # set up initially
    entry = await setup_platform(menuai)
    result = await entry.start_reauth_flow(menuai)

    with patch(
        "menuai.components.sleepiq.config_flow.AsyncSleepIQ.login",
        return_value=True,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"password": "password"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
