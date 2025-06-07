"""Define tests for the Airzone Cloud config flow."""

from unittest.mock import patch

from aioairzone_cloud.exceptions import AirzoneCloudError, LoginError

from menuai.components.airzone_cloud.const import DOMAIN
from menuai.config_entries import SOURCE_USER, ConfigEntryState
from menuai.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .util import (
    CONFIG,
    GET_INSTALLATION_MOCK,
    GET_INSTALLATIONS_MOCK,
    WS_ID,
    mock_get_device_config,
    mock_get_device_status,
    mock_get_webserver,
)


async def test_form(menuai: menuai) -> None:
    """Test that the form is served with valid input."""

    with (
        patch(
            "menuai.components.airzone_cloud.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_get_device_config",
            side_effect=mock_get_device_config,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_get_device_status",
            side_effect=mock_get_device_status,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_get_installation",
            return_value=GET_INSTALLATION_MOCK,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_get_installations",
            return_value=GET_INSTALLATIONS_MOCK,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_get_webserver",
            side_effect=mock_get_webserver,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.login",
            return_value=None,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: CONFIG[CONF_USERNAME],
                CONF_PASSWORD: CONFIG[CONF_PASSWORD],
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ID: CONFIG[CONF_ID],
            },
        )

        await menuai.async_block_till_done()

        conf_entries = menuai.config_entries.async_entries(DOMAIN)
        entry = conf_entries[0]
        assert entry.state is ConfigEntryState.LOADED

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == f"House {WS_ID} ({CONFIG[CONF_ID]})"
        assert result["data"][CONF_ID] == CONFIG[CONF_ID]
        assert result["data"][CONF_USERNAME] == CONFIG[CONF_USERNAME]
        assert result["data"][CONF_PASSWORD] == CONFIG[CONF_PASSWORD]

        assert len(mock_setup_entry.mock_calls) == 1


async def test_installations_list_error(menuai: menuai) -> None:
    """Test connection error."""

    with (
        patch(
            "menuai.components.airzone_cloud.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_get_device_config",
            side_effect=mock_get_device_config,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_get_device_status",
            side_effect=mock_get_device_status,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_get_installations",
            side_effect=AirzoneCloudError,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_get_webserver",
            side_effect=mock_get_webserver,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.login",
            return_value=None,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: CONFIG[CONF_USERNAME],
                CONF_PASSWORD: CONFIG[CONF_PASSWORD],
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}


async def test_login_error(menuai: menuai) -> None:
    """Test login error."""

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.login",
        side_effect=LoginError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_USERNAME: CONFIG[CONF_USERNAME],
                CONF_PASSWORD: CONFIG[CONF_PASSWORD],
            },
        )

        assert result["errors"] == {"base": "cannot_connect"}
