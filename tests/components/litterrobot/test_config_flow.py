"""Test the Litter-Robot config flow."""

from unittest.mock import patch

from pylitterbot import Account
from pylitterbot.exceptions import LitterRobotException, LitterRobotLoginException
import pytest

from menuai import config_entries
from menuai.const import CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .common import CONF_USERNAME, CONFIG, DOMAIN

from tests.common import MockConfigEntry


async def test_full_flow(menuai: menuai, mock_account) -> None:
    """Test full flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.litterrobot.config_flow.Account.connect",
            return_value=mock_account,
        ),
        patch(
            "menuai.components.litterrobot.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG[DOMAIN]
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == CONFIG[DOMAIN][CONF_USERNAME]
    assert result["data"] == CONFIG[DOMAIN]
    assert len(mock_setup_entry.mock_calls) == 1


async def test_already_configured(menuai: menuai) -> None:
    """Test already configured case."""
    MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG[DOMAIN],
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=CONFIG[DOMAIN],
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("side_effect", "connect_errors"),
    [
        (Exception, {"base": "unknown"}),
        (LitterRobotLoginException, {"base": "invalid_auth"}),
        (LitterRobotException, {"base": "cannot_connect"}),
    ],
)
async def test_create_entry(
    menuai: menuai, mock_account, side_effect, connect_errors
) -> None:
    """Test creating an entry."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.litterrobot.config_flow.Account.connect",
        side_effect=side_effect,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG[DOMAIN]
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == connect_errors

    with (
        patch(
            "menuai.components.litterrobot.config_flow.Account.connect",
            return_value=mock_account,
        ),
        patch(
            "menuai.components.litterrobot.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG[DOMAIN]
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == CONFIG[DOMAIN][CONF_USERNAME]
    assert result["data"] == CONFIG[DOMAIN]


async def test_reauth(menuai: menuai, mock_account: Account) -> None:
    """Test reauth flow (with fail and recover)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG[DOMAIN],
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "menuai.components.litterrobot.config_flow.Account.connect",
        side_effect=LitterRobotLoginException,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: CONFIG[DOMAIN][CONF_PASSWORD]},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}

    with (
        patch(
            "menuai.components.litterrobot.config_flow.Account.connect",
            return_value=mock_account,
        ),
        patch(
            "menuai.components.litterrobot.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: CONFIG[DOMAIN][CONF_PASSWORD]},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"
        assert len(mock_setup_entry.mock_calls) == 1
