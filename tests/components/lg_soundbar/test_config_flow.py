"""Test the lg_soundbar config flow."""

from __future__ import annotations

from collections.abc import Callable
import socket
from typing import Any
from unittest.mock import DEFAULT, MagicMock, patch

from menuai import config_entries
from menuai.components.lg_soundbar.const import DEFAULT_PORT, DOMAIN
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


def setup_mock_temescal(
    menuai: menuai,
    mock_temescal: MagicMock,
    mac_info_dev: dict[str, Any] | None = None,
    product_info: dict[str, Any] | None = None,
    info: dict[str, Any] | None = None,
) -> None:
    """Set up a mock of the temescal object to craft our expected responses."""
    tmock = mock_temescal.temescal
    instance = tmock.return_value

    def create_temescal_response(msg: str, data: dict | None = None) -> dict[str, Any]:
        response: dict[str, Any] = {"msg": msg}
        if data is not None:
            response["data"] = data
        return response

    def temescal_side_effect(
        addr: str, port: int, callback: Callable[[dict[str, Any]], None]
    ):
        mac_info_response = create_temescal_response(
            msg="MAC_INFO_DEV", data=mac_info_dev
        )
        product_info_response = create_temescal_response(
            msg="PRODUCT_INFO", data=product_info
        )
        info_response = create_temescal_response(msg="SPK_LIST_VIEW_INFO", data=info)

        instance.get_mac_info.side_effect = lambda: menuai.add_job(
            callback, mac_info_response
        )
        instance.get_product_info.side_effect = lambda: menuai.add_job(
            callback, product_info_response
        )
        instance.get_info.side_effect = lambda: menuai.add_job(callback, info_response)

        return DEFAULT

    tmock.side_effect = temescal_side_effect


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.lg_soundbar.config_flow.temescal"
        ) as mock_temescal,
        patch(
            "menuai.components.lg_soundbar.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        setup_mock_temescal(
            menuai=menuai,
            mock_temescal=mock_temescal,
            mac_info_dev={"s_uuid": "uuid"},
            info={"s_user_name": "name"},
        )
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "name"
    assert result2["result"].unique_id == "uuid"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: DEFAULT_PORT,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_mac_info_response_empty(menuai: menuai) -> None:
    """Test we get the form, but response from the initial get_mac_info function call is empty."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.lg_soundbar.config_flow.temescal"
        ) as mock_temescal,
        patch(
            "menuai.components.lg_soundbar.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        setup_mock_temescal(
            menuai=menuai,
            mock_temescal=mock_temescal,
            mac_info_dev={"s_uuid": "uuid"},
            info={"s_user_name": "name"},
        )
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "name"
    assert result2["result"].unique_id == "uuid"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: DEFAULT_PORT,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_uuid_present_in_both_functions_uuid_q_empty(
    menuai: menuai,
) -> None:
    """Get the form, uuid present in both get_mac_info and get_product_info calls.

    Value from get_mac_info is not added to uuid_q before get_product_info is run.
    """

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.lg_soundbar.config_flow.temescal"
        ) as mock_temescal,
        patch(
            "menuai.components.lg_soundbar.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        setup_mock_temescal(
            menuai=menuai,
            mock_temescal=mock_temescal,
            mac_info_dev={"s_uuid": "uuid"},
            product_info={"s_uuid": "uuid"},
            info={"s_user_name": "name"},
        )

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "name"
    assert result2["result"].unique_id == "uuid"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: DEFAULT_PORT,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_uuid_present_in_both_functions_uuid_q_not_empty(
    menuai: menuai,
) -> None:
    """Get the form, uuid present in both get_mac_info and get_product_info calls.

    Value from get_mac_info is added to uuid_q before get_product_info is run.
    """

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.lg_soundbar.config_flow.QUEUE_TIMEOUT",
            new=0.1,
        ),
        patch(
            "menuai.components.lg_soundbar.config_flow.temescal"
        ) as mock_temescal,
        patch(
            "menuai.components.lg_soundbar.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        setup_mock_temescal(
            menuai=menuai,
            mock_temescal=mock_temescal,
            mac_info_dev={"s_uuid": "uuid"},
            product_info={"s_uuid": "uuid"},
            info={"s_user_name": "name"},
        )

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "name"
    assert result2["result"].unique_id == "uuid"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: DEFAULT_PORT,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_uuid_missing_from_mac_info(menuai: menuai) -> None:
    """Test we get the form, but uuid is missing from the initial get_mac_info function call."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.lg_soundbar.config_flow.temescal"
        ) as mock_temescal,
        patch(
            "menuai.components.lg_soundbar.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        setup_mock_temescal(
            menuai=menuai,
            mock_temescal=mock_temescal,
            product_info={"s_uuid": "uuid"},
            info={"s_user_name": "name"},
        )

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "name"
    assert result2["result"].unique_id == "uuid"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: DEFAULT_PORT,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_uuid_not_provided_by_api(menuai: menuai) -> None:
    """Test we get the form, but uuid is missing from the all API messages."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.lg_soundbar.config_flow.QUEUE_TIMEOUT",
            new=0.1,
        ),
        patch(
            "menuai.components.lg_soundbar.config_flow.temescal"
        ) as mock_temescal,
        patch(
            "menuai.components.lg_soundbar.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        setup_mock_temescal(
            menuai=menuai,
            mock_temescal=mock_temescal,
            product_info={"i_model_no": "8", "i_model_type": 0},
            info={"s_user_name": "name"},
        )
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "name"
    assert result2["result"].unique_id is None
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: DEFAULT_PORT,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_both_queues_empty(menuai: menuai) -> None:
    """Test we get the form, but none of the data we want is provided by the API."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.lg_soundbar.config_flow.QUEUE_TIMEOUT",
            new=0.1,
        ),
        patch(
            "menuai.components.lg_soundbar.config_flow.temescal"
        ) as mock_temescal,
        patch(
            "menuai.components.lg_soundbar.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        setup_mock_temescal(menuai=menuai, mock_temescal=mock_temescal)

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "no_data"}
    assert len(mock_setup_entry.mock_calls) == 0


async def test_no_uuid_host_already_configured(menuai: menuai) -> None:
    """Test we handle if the device has no UUID and the host has already been configured."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "1.1.1.1",
            CONF_PORT: DEFAULT_PORT,
        },
    )
    mock_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.lg_soundbar.config_flow.QUEUE_TIMEOUT",
            new=0.1,
        ),
        patch(
            "menuai.components.lg_soundbar.config_flow.temescal"
        ) as mock_temescal,
    ):
        setup_mock_temescal(
            menuai=menuai, mock_temescal=mock_temescal, info={"s_user_name": "name"}
        )
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_form_socket_timeout(menuai: menuai) -> None:
    """Test we handle socket.timeout error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.lg_soundbar.config_flow.temescal"
    ) as mock_temescal:
        mock_temescal.temescal.side_effect = socket.timeout
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_os_error(menuai: menuai) -> None:
    """Test we handle OSError."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.lg_soundbar.config_flow.temescal"
    ) as mock_temescal:
        mock_temescal.temescal.side_effect = OSError
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_already_configured(menuai: menuai) -> None:
    """Test we handle already configured error."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "1.1.1.1",
            CONF_PORT: 0000,
        },
        unique_id="uuid",
    )
    mock_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.lg_soundbar.config_flow.temescal"
    ) as mock_temescal:
        setup_mock_temescal(
            menuai=menuai,
            mock_temescal=mock_temescal,
            mac_info_dev={"s_uuid": "uuid"},
            info={"s_user_name": "name"},
        )

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
            },
        )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
