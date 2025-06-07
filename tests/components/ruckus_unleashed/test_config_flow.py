"""Test the config flow."""

from copy import deepcopy
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from aioruckus.const import (
    ERROR_CONNECT_TEMPORARY,
    ERROR_CONNECT_TIMEOUT,
    ERROR_LOGIN_INCORRECT,
)
from aioruckus.exceptions import AuthenticationError

from menuai import config_entries
from menuai.components.ruckus_unleashed.const import (
    API_SYS_SYSINFO,
    API_SYS_SYSINFO_SERIAL,
    DOMAIN,
)
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.util import utcnow

from . import (
    CONFIG,
    DEFAULT_SYSTEM_INFO,
    DEFAULT_TITLE,
    RuckusAjaxApiPatchContext,
    mock_config_entry,
)

from tests.common import async_fire_time_changed


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        RuckusAjaxApiPatchContext(),
        patch(
            "menuai.components.ruckus_unleashed.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )
        await menuai.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == DEFAULT_TITLE
    assert result2["data"] == CONFIG


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with RuckusAjaxApiPatchContext(
        login_mock=AsyncMock(side_effect=AuthenticationError(ERROR_LOGIN_INCORRECT))
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_user_reauth(menuai: menuai) -> None:
    """Test reauth."""
    entry = mock_config_entry()
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert "flow_id" in flows[0]

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with RuckusAjaxApiPatchContext():
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.2.3.4",
                CONF_USERNAME: "new_name",
                CONF_PASSWORD: "new_pass",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"


async def test_form_user_reauth_different_unique_id(menuai: menuai) -> None:
    """Test reauth."""
    entry = mock_config_entry()
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert "flow_id" in flows[0]

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    system_info = deepcopy(DEFAULT_SYSTEM_INFO)
    system_info[API_SYS_SYSINFO][API_SYS_SYSINFO_SERIAL] = "000000000"
    with RuckusAjaxApiPatchContext(system_info=system_info):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.2.3.4",
                CONF_USERNAME: "new_name",
                CONF_PASSWORD: "new_pass",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_host"}


async def test_form_user_reauth_invalid_auth(menuai: menuai) -> None:
    """Test reauth."""
    entry = mock_config_entry()
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert "flow_id" in flows[0]

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with RuckusAjaxApiPatchContext(
        login_mock=AsyncMock(side_effect=AuthenticationError(ERROR_LOGIN_INCORRECT))
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.2.3.4",
                CONF_USERNAME: "new_name",
                CONF_PASSWORD: "new_pass",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_user_reauth_cannot_connect(menuai: menuai) -> None:
    """Test reauth."""
    entry = mock_config_entry()
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert "flow_id" in flows[0]

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with RuckusAjaxApiPatchContext(
        login_mock=AsyncMock(side_effect=ConnectionError(ERROR_CONNECT_TIMEOUT))
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.2.3.4",
                CONF_USERNAME: "new_name",
                CONF_PASSWORD: "new_pass",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_user_reauth_general_exception(menuai: menuai) -> None:
    """Test reauth."""
    entry = mock_config_entry()
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert "flow_id" in flows[0]

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with RuckusAjaxApiPatchContext(login_mock=AsyncMock(side_effect=Exception)):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.2.3.4",
                CONF_USERNAME: "new_name",
                CONF_PASSWORD: "new_pass",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "unknown"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with RuckusAjaxApiPatchContext(
        login_mock=AsyncMock(side_effect=ConnectionError(ERROR_CONNECT_TIMEOUT))
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_general_exception(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with RuckusAjaxApiPatchContext(login_mock=AsyncMock(side_effect=Exception)):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "unknown"}


async def test_form_unexpected_response(menuai: menuai) -> None:
    """Test we handle unknown error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with RuckusAjaxApiPatchContext(
        login_mock=AsyncMock(
            side_effect=ConnectionRefusedError(ERROR_CONNECT_TEMPORARY)
        )
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_duplicate_error(menuai: menuai) -> None:
    """Test we handle duplicate error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with RuckusAjaxApiPatchContext():
        await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

        future = utcnow() + timedelta(minutes=60)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {}

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            CONFIG,
        )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
