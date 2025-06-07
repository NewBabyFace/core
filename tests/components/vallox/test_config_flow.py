"""Test the Vallox integration config flow."""

from unittest.mock import patch

from vallox_websocket_api import ValloxApiException, ValloxWebsocketException

from menuai.components.vallox.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import create_mock_entry, do_setup_vallox_entry


async def test_form_no_input(menuai: menuai) -> None:
    """Test that the form is returned with no input."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None


async def test_form_create_entry(menuai: menuai) -> None:
    """Test that an entry is created with valid input."""
    init = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert init["type"] is FlowResultType.FORM
    assert init["errors"] is None

    with (
        patch(
            "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
            return_value=None,
        ),
        patch(
            "menuai.components.vallox.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            init["flow_id"],
            {"host": "1.2.3.4"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vallox"
    assert result["data"] == {"host": "1.2.3.4", "name": "Vallox"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_ip(menuai: menuai) -> None:
    """Test that invalid IP error is handled."""
    init = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        init["flow_id"],
        {"host": "test.host.com"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"host": "invalid_host"}

    with (
        patch(
            "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
            return_value=None,
        ),
        patch(
            "menuai.components.vallox.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            init["flow_id"],
            {"host": "1.2.3.4"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vallox"
    assert result["data"] == {"host": "1.2.3.4", "name": "Vallox"}


async def test_form_vallox_api_exception_cannot_connect(menuai: menuai) -> None:
    """Test that cannot connect error is handled."""
    init = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
        side_effect=ValloxApiException,
    ):
        result = await menuai.config_entries.flow.async_configure(
            init["flow_id"],
            {"host": "4.3.2.1"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"host": "cannot_connect"}

    with (
        patch(
            "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
            return_value=None,
        ),
        patch(
            "menuai.components.vallox.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            init["flow_id"],
            {"host": "1.2.3.4"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vallox"
    assert result["data"] == {"host": "1.2.3.4", "name": "Vallox"}


async def test_form_os_error_cannot_connect(menuai: menuai) -> None:
    """Test that cannot connect error is handled."""
    init = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
        side_effect=ValloxWebsocketException,
    ):
        result = await menuai.config_entries.flow.async_configure(
            init["flow_id"],
            {"host": "5.6.7.8"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"host": "cannot_connect"}

    with (
        patch(
            "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
            return_value=None,
        ),
        patch(
            "menuai.components.vallox.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            init["flow_id"],
            {"host": "1.2.3.4"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vallox"
    assert result["data"] == {"host": "1.2.3.4", "name": "Vallox"}


async def test_form_unknown_exception(menuai: menuai) -> None:
    """Test that unknown exceptions are handled."""
    init = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
        side_effect=Exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            init["flow_id"],
            {"host": "54.12.31.41"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"host": "unknown"}

    with (
        patch(
            "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
            return_value=None,
        ),
        patch(
            "menuai.components.vallox.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            init["flow_id"],
            {"host": "1.2.3.4"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Vallox"
    assert result["data"] == {"host": "1.2.3.4", "name": "Vallox"}


async def test_form_already_configured(menuai: menuai) -> None:
    """Test that already configured error is handled."""
    init = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    create_mock_entry(menuai, "20.40.10.30", "Vallox 110 MV")

    result = await menuai.config_entries.flow.async_configure(
        init["flow_id"],
        {"host": "20.40.10.30"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_host(menuai: menuai, init_reconfigure_flow) -> None:
    """Test that the host can be reconfigured."""
    entry, init_flow_result = init_reconfigure_flow

    reconfigure_result = await menuai.config_entries.flow.async_configure(
        init_flow_result["flow_id"],
        {
            "host": "192.168.100.60",
        },
    )
    await menuai.async_block_till_done()
    assert reconfigure_result["type"] is FlowResultType.ABORT
    assert reconfigure_result["reason"] == "reconfigure_successful"

    # changed entry
    assert entry.data["host"] == "192.168.100.60"


async def test_reconfigure_host_to_same_host_as_another_fails(
    menuai: menuai, init_reconfigure_flow
) -> None:
    """Test that changing host to a host that already exists fails."""
    entry, init_flow_result = init_reconfigure_flow

    # Create second device
    create_mock_entry(menuai=menuai, host="192.168.100.70", name="Vallox 2")
    await do_setup_vallox_entry(menuai=menuai, host="192.168.100.70", name="Vallox 2")

    reconfigure_result = await menuai.config_entries.flow.async_configure(
        init_flow_result["flow_id"],
        {
            "host": "192.168.100.70",
        },
    )
    await menuai.async_block_till_done()
    assert reconfigure_result["type"] is FlowResultType.ABORT
    assert reconfigure_result["reason"] == "already_configured"

    # entry not changed
    assert entry.data["host"] == "192.168.100.50"


async def test_reconfigure_host_to_invalid_ip_fails(
    menuai: menuai, init_reconfigure_flow
) -> None:
    """Test that an invalid IP error is handled by the reconfigure step."""
    entry, init_flow_result = init_reconfigure_flow

    reconfigure_result = await menuai.config_entries.flow.async_configure(
        init_flow_result["flow_id"],
        {
            "host": "test.host.com",
        },
    )
    await menuai.async_block_till_done()
    assert reconfigure_result["type"] is FlowResultType.FORM
    assert reconfigure_result["errors"] == {"host": "invalid_host"}

    # entry not changed
    assert entry.data["host"] == "192.168.100.50"

    # makes sure we can recover and continue
    reconfigure_result = await menuai.config_entries.flow.async_configure(
        init_flow_result["flow_id"],
        {
            "host": "192.168.100.60",
        },
    )
    await menuai.async_block_till_done()
    assert reconfigure_result["type"] is FlowResultType.ABORT
    assert reconfigure_result["reason"] == "reconfigure_successful"

    # changed entry
    assert entry.data["host"] == "192.168.100.60"


async def test_reconfigure_host_vallox_api_exception_cannot_connect(
    menuai: menuai, init_reconfigure_flow
) -> None:
    """Test that cannot connect error is handled by the reconfigure step."""
    entry, init_flow_result = init_reconfigure_flow

    with patch(
        "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
        side_effect=ValloxApiException,
    ):
        reconfigure_result = await menuai.config_entries.flow.async_configure(
            init_flow_result["flow_id"],
            {
                "host": "192.168.100.80",
            },
        )
        await menuai.async_block_till_done()

    assert reconfigure_result["type"] is FlowResultType.FORM
    assert reconfigure_result["errors"] == {"host": "cannot_connect"}

    # entry not changed
    assert entry.data["host"] == "192.168.100.50"

    # makes sure we can recover and continue
    reconfigure_result = await menuai.config_entries.flow.async_configure(
        init_flow_result["flow_id"],
        {
            "host": "192.168.100.60",
        },
    )
    await menuai.async_block_till_done()
    assert reconfigure_result["type"] is FlowResultType.ABORT
    assert reconfigure_result["reason"] == "reconfigure_successful"

    # changed entry
    assert entry.data["host"] == "192.168.100.60"


async def test_reconfigure_host_unknown_exception(
    menuai: menuai, init_reconfigure_flow
) -> None:
    """Test that cannot connect error is handled by the reconfigure step."""
    entry, init_flow_result = init_reconfigure_flow

    with patch(
        "menuai.components.vallox.config_flow.Vallox.fetch_metric_data",
        side_effect=Exception,
    ):
        reconfigure_result = await menuai.config_entries.flow.async_configure(
            init_flow_result["flow_id"],
            {
                "host": "192.168.100.90",
            },
        )
        await menuai.async_block_till_done()

    assert reconfigure_result["type"] is FlowResultType.FORM
    assert reconfigure_result["errors"] == {"host": "unknown"}

    # entry not changed
    assert entry.data["host"] == "192.168.100.50"

    # makes sure we can recover and continue
    reconfigure_result = await menuai.config_entries.flow.async_configure(
        init_flow_result["flow_id"],
        {
            "host": "192.168.100.60",
        },
    )
    await menuai.async_block_till_done()
    assert reconfigure_result["type"] is FlowResultType.ABORT
    assert reconfigure_result["reason"] == "reconfigure_successful"

    # changed entry
    assert entry.data["host"] == "192.168.100.60"
