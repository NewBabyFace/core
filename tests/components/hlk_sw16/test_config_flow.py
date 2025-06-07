"""Test the Hi-Link HLK-SW16 config flow."""

import asyncio
from unittest.mock import patch

from menuai import config_entries
from menuai.components.hlk_sw16.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


class MockSW16Client:
    """Class to mock the SW16Client client."""

    def __init__(self, fail) -> None:
        """Initialise client with failure modes."""
        self.fail = fail
        self.disconnect_callback = None
        self.in_transaction = False
        self.active_transaction = None

    async def setup(self):
        """Mock successful setup."""
        fut = asyncio.Future()
        fut.set_result(True)
        return fut

    async def status(self):
        """Mock status based on failure mode."""
        self.in_transaction = True
        self.active_transaction = asyncio.Future()
        if self.fail:
            if self.disconnect_callback:
                self.disconnect_callback()
            return await self.active_transaction
        self.active_transaction.set_result(True)
        return self.active_transaction

    def stop(self):
        """Mock client stop."""
        self.in_transaction = False
        self.active_transaction = None


async def create_mock_hlk_sw16_connection(fail):
    """Create a mock HLK-SW16 client."""
    client = MockSW16Client(fail)
    await client.setup()
    return client


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    conf = {
        "host": "127.0.0.1",
        "port": 8080,
    }

    mock_hlk_sw16_connection = await create_mock_hlk_sw16_connection(False)

    with (
        patch(
            "menuai.components.hlk_sw16.config_flow.create_hlk_sw16_connection",
            return_value=mock_hlk_sw16_connection,
        ),
        patch(
            "menuai.components.hlk_sw16.async_setup", return_value=True
        ) as mock_setup,
        patch(
            "menuai.components.hlk_sw16.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            conf,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "127.0.0.1:8080"
    assert result2["data"] == {
        "host": "127.0.0.1",
        "port": 8080,
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1

    mock_hlk_sw16_connection = await create_mock_hlk_sw16_connection(False)

    with patch(
        "menuai.components.hlk_sw16.config_flow.create_hlk_sw16_connection",
        return_value=mock_hlk_sw16_connection,
    ):
        result3 = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {}

    result4 = await menuai.config_entries.flow.async_configure(
        result3["flow_id"],
        conf,
    )

    assert result4["type"] is FlowResultType.ABORT
    assert result4["reason"] == "already_configured"


async def test_import(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_IMPORT}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    conf = {
        "host": "127.0.0.1",
        "port": 8080,
    }

    mock_hlk_sw16_connection = await create_mock_hlk_sw16_connection(False)

    with (
        patch(
            "menuai.components.hlk_sw16.config_flow.connect_client",
            return_value=mock_hlk_sw16_connection,
        ),
        patch(
            "menuai.components.hlk_sw16.async_setup", return_value=True
        ) as mock_setup,
        patch(
            "menuai.components.hlk_sw16.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            conf,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "127.0.0.1:8080"
    assert result2["data"] == {
        "host": "127.0.0.1",
        "port": 8080,
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_data(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_hlk_sw16_connection = await create_mock_hlk_sw16_connection(True)

    conf = {
        "host": "127.0.0.1",
        "port": 8080,
    }

    with patch(
        "menuai.components.hlk_sw16.config_flow.connect_client",
        return_value=mock_hlk_sw16_connection,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            conf,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    conf = {
        "host": "127.0.0.1",
        "port": 8080,
    }

    with patch(
        "menuai.components.hlk_sw16.config_flow.connect_client",
        side_effect=TimeoutError,
        return_value=None,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            conf,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
