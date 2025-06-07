"""Test the Logitech Squeezebox config flow."""

from http import HTTPStatus
from unittest.mock import patch

from pysqueezebox import Server

from menuai import config_entries
from menuai.components.squeezebox.const import (
    CONF_BROWSE_LIMIT,
    CONF_HTTPS,
    CONF_VOLUME_STEP,
    DOMAIN,
)
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from tests.common import MockConfigEntry

HOST = "1.1.1.1"
HOST2 = "2.2.2.2"
PORT = 9000
UUID = "test-uuid"
UNKNOWN_ERROR = "1234"
BROWSE_LIMIT = 10
VOLUME_STEP = 1


async def mock_discover(_discovery_callback):
    """Mock discovering a Logitech Media Server."""
    _discovery_callback(Server(None, HOST, PORT, uuid=UUID))


async def mock_failed_discover(_discovery_callback):
    """Mock unsuccessful discovery by doing nothing."""


async def patch_async_query_unauthorized(self, *args):
    """Mock an unauthorized query."""
    self.http_status = HTTPStatus.UNAUTHORIZED
    return False


async def test_user_form(menuai: menuai) -> None:
    """Test user-initiated flow, including discovery and the edit step."""
    with (
        patch(
            "pysqueezebox.Server.async_query",
            return_value={"uuid": UUID},
        ),
        patch(
            "menuai.components.squeezebox.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.squeezebox.config_flow.async_discover",
            mock_discover,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "edit"
        assert CONF_HOST in result["data_schema"].schema
        for key in result["data_schema"].schema:
            if key == CONF_HOST:
                assert key.description == {"suggested_value": HOST}

        # test the edit step
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_HTTPS: False,
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == HOST
        assert result["data"] == {
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_HTTPS: False,
        }

        await menuai.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1


async def test_options_form(menuai: menuai) -> None:
    """Test we can configure options."""
    entry = MockConfigEntry(
        data={
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_HTTPS: False,
        },
        unique_id=UUID,
        domain=DOMAIN,
        options={CONF_BROWSE_LIMIT: 1000, CONF_VOLUME_STEP: 5},
    )

    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # simulate manual input of options
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_BROWSE_LIMIT: BROWSE_LIMIT, CONF_VOLUME_STEP: VOLUME_STEP},
    )

    # put some meaningful asserts here
    assert result["type"] is FlowResultType.CREATE_ENTRY

    assert result["data"] == {
        CONF_BROWSE_LIMIT: BROWSE_LIMIT,
        CONF_VOLUME_STEP: VOLUME_STEP,
    }


async def test_user_form_timeout(menuai: menuai) -> None:
    """Test we handle server search timeout."""
    with (
        patch(
            "menuai.components.squeezebox.config_flow.async_discover",
            mock_failed_discover,
        ),
        patch("menuai.components.squeezebox.config_flow.TIMEOUT", 0.1),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "no_server_found"}

        # simulate manual input of host
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: HOST2}
        )
        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "edit"
        assert CONF_HOST in result2["data_schema"].schema
        for key in result2["data_schema"].schema:
            if key == CONF_HOST:
                assert key.description == {"suggested_value": HOST2}


async def test_user_form_duplicate(menuai: menuai) -> None:
    """Test duplicate discovered servers are skipped."""
    with (
        patch(
            "menuai.components.squeezebox.config_flow.async_discover",
            mock_discover,
        ),
        patch("menuai.components.squeezebox.config_flow.TIMEOUT", 0.1),
        patch(
            "menuai.components.squeezebox.async_setup_entry",
            return_value=True,
        ),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=UUID,
            data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_HTTPS: False},
        )
        entry.add_to_menuai(menuai)

        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "no_server_found"}


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""

    async def patch_async_query(self, *args):
        self.http_status = HTTPStatus.UNAUTHORIZED
        return False

    with (
        patch(
            "pysqueezebox.Server.async_query",
            return_value={"uuid": UUID},
        ),
        patch(
            "menuai.components.squeezebox.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.squeezebox.config_flow.async_discover",
            mock_discover,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "edit"

        with patch(
            "menuai.components.squeezebox.config_flow.Server.async_query",
            new=patch_async_query,
        ):
            result = await menuai.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: HOST,
                    CONF_PORT: PORT,
                    CONF_USERNAME: "test-username",
                    CONF_PASSWORD: "test-password",
                },
            )

            assert result["type"] is FlowResultType.FORM
            assert result["errors"] == {"base": "invalid_auth"}

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_HTTPS: False,
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == HOST
        assert result["data"] == {
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_HTTPS: False,
        }


async def test_form_validate_exception(menuai: menuai) -> None:
    """Test we handle exception."""

    with (
        patch(
            "pysqueezebox.Server.async_query",
            return_value={"uuid": UUID},
        ),
        patch(
            "menuai.components.squeezebox.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.squeezebox.config_flow.async_discover",
            mock_discover,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "edit"

        with patch(
            "menuai.components.squeezebox.config_flow.Server.async_query",
            side_effect=Exception,
        ):
            result = await menuai.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: HOST,
                    CONF_PORT: PORT,
                    CONF_USERNAME: "",
                    CONF_PASSWORD: "",
                },
            )

            assert result["type"] is FlowResultType.FORM
            assert result["errors"] == {"base": "unknown"}

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_HTTPS: False,
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == HOST
        assert result["data"] == {
            CONF_HOST: HOST,
            CONF_PORT: PORT,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_HTTPS: False,
        }


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "edit"}
    )

    with patch(
        "pysqueezebox.Server.async_query",
        return_value=False,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_discovery(menuai: menuai) -> None:
    """Test handling of discovered server."""
    with patch(
        "pysqueezebox.Server.async_query",
        return_value={"uuid": UUID},
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={CONF_HOST: HOST, CONF_PORT: PORT, "uuid": UUID},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "edit"


async def test_discovery_no_uuid(menuai: menuai) -> None:
    """Test handling of discovered server with unavailable uuid."""
    with patch("pysqueezebox.Server.async_query", new=patch_async_query_unauthorized):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={CONF_HOST: HOST, CONF_PORT: PORT, CONF_HTTPS: False},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "edit"


async def test_dhcp_discovery(menuai: menuai) -> None:
    """Test we can process discovery from dhcp."""
    with (
        patch(
            "pysqueezebox.Server.async_query",
            return_value={"uuid": UUID},
        ),
        patch(
            "menuai.components.squeezebox.config_flow.async_discover",
            mock_discover,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                ip="1.1.1.1",
                macaddress="aabbccddeeff",
                hostname="any",
            ),
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "edit"


async def test_dhcp_discovery_no_server_found(menuai: menuai) -> None:
    """Test we can handle dhcp discovery when no server is found."""
    with (
        patch(
            "menuai.components.squeezebox.config_flow.async_discover",
            mock_failed_discover,
        ),
        patch("menuai.components.squeezebox.config_flow.TIMEOUT", 0.1),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                ip="1.1.1.1",
                macaddress="aabbccddeeff",
                hostname="any",
            ),
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"


async def test_dhcp_discovery_existing_player(menuai: menuai) -> None:
    """Test that we properly ignore known players during dhcp discover."""
    with patch(
        "menuai.helpers.entity_registry.EntityRegistry.async_get_entity_id",
        return_value="test_entity",
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                ip="1.1.1.1",
                macaddress="aabbccddeeff",
                hostname="any",
            ),
        )
        assert result["type"] is FlowResultType.ABORT
