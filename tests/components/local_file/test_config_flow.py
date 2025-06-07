"""Test the Scrape config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from menuai import config_entries
from menuai.components.local_file.const import DEFAULT_NAME, DOMAIN
from menuai.const import CONF_FILE_PATH, CONF_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form_sensor(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form for sensor."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    with (
        patch("os.path.isfile", Mock(return_value=True)),
        patch("os.access", Mock(return_value=True)),
        patch(
            "menuai.components.local_file.camera.mimetypes.guess_type",
            Mock(return_value=(None, None)),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: DEFAULT_NAME,
                CONF_FILE_PATH: "mock.file",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["version"] == 1
    assert result["options"] == {
        CONF_NAME: DEFAULT_NAME,
        CONF_FILE_PATH: "mock.file",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_options_flow(menuai: menuai, loaded_entry: MockConfigEntry) -> None:
    """Test options flow."""

    result = await menuai.config_entries.options.async_init(loaded_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    with (
        patch("os.path.isfile", Mock(return_value=True)),
        patch("os.access", Mock(return_value=True)),
        patch(
            "menuai.components.local_file.camera.mimetypes.guess_type",
            Mock(return_value=(None, None)),
        ),
    ):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_FILE_PATH: "mock.new.file"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_NAME: DEFAULT_NAME, CONF_FILE_PATH: "mock.new.file"}

    await menuai.async_block_till_done()

    # Check the entity was updated, no new entity was created
    assert len(menuai.states.async_all()) == 1

    state = menuai.states.get("camera.local_file")
    assert state is not None


async def test_validation_options(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test validation."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    with (
        patch("os.path.isfile", Mock(return_value=True)),
        patch("os.access", Mock(return_value=False)),
        patch(
            "menuai.components.local_file.camera.mimetypes.guess_type",
            Mock(return_value=(None, None)),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: DEFAULT_NAME,
                CONF_FILE_PATH: "mock.file",
            },
        )
        await menuai.async_block_till_done()

    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "not_readable_path"}

    with (
        patch("os.path.isfile", Mock(return_value=True)),
        patch("os.access", Mock(return_value=True)),
        patch(
            "menuai.components.local_file.camera.mimetypes.guess_type",
            Mock(return_value=(None, None)),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: DEFAULT_NAME,
                CONF_FILE_PATH: "mock.new.file",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["version"] == 1
    assert result["options"] == {
        CONF_NAME: DEFAULT_NAME,
        CONF_FILE_PATH: "mock.new.file",
    }

    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("mock_setup_entry")
async def test_entry_already_exist(
    menuai: menuai, loaded_entry: MockConfigEntry
) -> None:
    """Test abort when entry already exist."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    with (
        patch("os.path.isfile", Mock(return_value=True)),
        patch("os.access", Mock(return_value=True)),
        patch(
            "menuai.components.local_file.camera.mimetypes.guess_type",
            Mock(return_value=(None, None)),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: DEFAULT_NAME,
                CONF_FILE_PATH: "mock.file",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
