"""Tests for OneDrive services."""

from collections.abc import Generator
from dataclasses import dataclass
import re
from typing import Any, cast
from unittest.mock import MagicMock, Mock, patch

from onedrive_personal_sdk.exceptions import OneDriveException
import pytest

from menuai.components.onedrive.const import DOMAIN
from menuai.components.onedrive.services import (
    CONF_CONFIG_ENTRY_ID,
    CONF_DESTINATION_FOLDER,
    UPLOAD_SERVICE,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_FILENAME
from menuai.core import menuai
from menuai.exceptions import menuaiError

from . import setup_integration

from tests.common import MockConfigEntry

TEST_FILENAME = "doorbell_snapshot.jpg"
DESINATION_FOLDER = "TestFolder"


@dataclass
class MockUploadFile:
    """Dataclass used to configure the test with a fake file behavior."""

    content: bytes = b"image bytes"
    exists: bool = True
    is_allowed_path: bool = True
    size: int | None = None


@pytest.fixture(name="upload_file")
def upload_file_fixture() -> MockUploadFile:
    """Fixture to set up test configuration with a fake file."""
    return MockUploadFile()


@pytest.fixture(autouse=True)
def mock_upload_file(
    menuai: menuai, upload_file: MockUploadFile
) -> Generator[None]:
    """Fixture that mocks out the file calls using the FakeFile fixture."""
    with (
        patch(
            "menuai.components.onedrive.services.Path.read_bytes",
            return_value=upload_file.content,
        ),
        patch(
            "menuai.components.onedrive.services.Path.exists",
            return_value=upload_file.exists,
        ),
        patch.object(
            menuai.config, "is_allowed_path", return_value=upload_file.is_allowed_path
        ),
        patch("pathlib.Path.stat") as mock_stat,
    ):
        mock_stat.return_value = Mock()
        mock_stat.return_value.st_size = (
            upload_file.size if upload_file.size else len(upload_file.content)
        )
        yield


async def test_upload_service(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test service call to upload content."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.services.has_service(DOMAIN, "upload")

    response = await menuai.services.async_call(
        DOMAIN,
        UPLOAD_SERVICE,
        {
            CONF_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            CONF_FILENAME: TEST_FILENAME,
            CONF_DESTINATION_FOLDER: DESINATION_FOLDER,
        },
        blocking=True,
        return_response=True,
    )

    assert response
    assert response["files"]
    assert cast(list[dict[str, Any]], response["files"])[0]["id"] == "id"


async def test_upload_service_no_response(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test service call to upload content without response."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.services.has_service(DOMAIN, "upload")

    response = await menuai.services.async_call(
        DOMAIN,
        UPLOAD_SERVICE,
        {
            CONF_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            CONF_FILENAME: TEST_FILENAME,
            CONF_DESTINATION_FOLDER: DESINATION_FOLDER,
        },
        blocking=True,
    )

    assert response is None


async def test_upload_service_config_entry_not_found(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test upload service call with a config entry that does not exist."""
    await setup_integration(menuai, mock_config_entry)
    with pytest.raises(menuaiError, match="not found in registry"):
        await menuai.services.async_call(
            DOMAIN,
            UPLOAD_SERVICE,
            {
                CONF_CONFIG_ENTRY_ID: "invalid-config-entry-id",
                CONF_FILENAME: TEST_FILENAME,
                CONF_DESTINATION_FOLDER: DESINATION_FOLDER,
            },
            blocking=True,
            return_response=True,
        )


async def test_config_entry_not_loaded(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test upload service call with a config entry that is not loaded."""
    await setup_integration(menuai, mock_config_entry)
    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED

    with pytest.raises(menuaiError, match="not found in registry"):
        await menuai.services.async_call(
            DOMAIN,
            UPLOAD_SERVICE,
            {
                CONF_CONFIG_ENTRY_ID: mock_config_entry.unique_id,
                CONF_FILENAME: TEST_FILENAME,
                CONF_DESTINATION_FOLDER: DESINATION_FOLDER,
            },
            blocking=True,
            return_response=True,
        )


@pytest.mark.parametrize("upload_file", [MockUploadFile(is_allowed_path=False)])
async def test_path_is_not_allowed(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test upload service call with a filename path that is not allowed."""
    await setup_integration(menuai, mock_config_entry)
    with (
        pytest.raises(menuaiError, match="no access to path"),
    ):
        await menuai.services.async_call(
            DOMAIN,
            UPLOAD_SERVICE,
            {
                CONF_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                CONF_FILENAME: TEST_FILENAME,
                CONF_DESTINATION_FOLDER: DESINATION_FOLDER,
            },
            blocking=True,
            return_response=True,
        )


@pytest.mark.parametrize("upload_file", [MockUploadFile(exists=False)])
async def test_filename_does_not_exist(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test upload service call with a filename path that does not exist."""
    await setup_integration(menuai, mock_config_entry)
    with pytest.raises(menuaiError, match="does not exist"):
        await menuai.services.async_call(
            DOMAIN,
            UPLOAD_SERVICE,
            {
                CONF_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                CONF_FILENAME: TEST_FILENAME,
                CONF_DESTINATION_FOLDER: DESINATION_FOLDER,
            },
            blocking=True,
            return_response=True,
        )


async def test_upload_service_fails_upload(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_onedrive_client: MagicMock,
) -> None:
    """Test service call to upload content."""
    await setup_integration(menuai, mock_config_entry)
    mock_onedrive_client.upload_file.side_effect = OneDriveException("error")

    with pytest.raises(menuaiError, match="Failed to upload"):
        await menuai.services.async_call(
            DOMAIN,
            UPLOAD_SERVICE,
            {
                CONF_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                CONF_FILENAME: TEST_FILENAME,
                CONF_DESTINATION_FOLDER: DESINATION_FOLDER,
            },
            blocking=True,
            return_response=True,
        )


@pytest.mark.parametrize("upload_file", [MockUploadFile(size=260 * 1024 * 1024)])
async def test_upload_size_limit(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test upload service call with a filename path that does not exist."""
    await setup_integration(menuai, mock_config_entry)
    with pytest.raises(
        menuaiError,
        match=re.escape(f"`{TEST_FILENAME}` is too large (272629760 > 262144000)"),
    ):
        await menuai.services.async_call(
            DOMAIN,
            UPLOAD_SERVICE,
            {
                CONF_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                CONF_FILENAME: TEST_FILENAME,
                CONF_DESTINATION_FOLDER: DESINATION_FOLDER,
            },
            blocking=True,
            return_response=True,
        )


async def test_create_album_failed(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_onedrive_client: MagicMock,
) -> None:
    """Test service call when folder creation fails."""
    await setup_integration(menuai, mock_config_entry)
    assert menuai.services.has_service(DOMAIN, "upload")

    mock_onedrive_client.create_folder.side_effect = OneDriveException()

    with pytest.raises(menuaiError, match="Failed to create folder"):
        await menuai.services.async_call(
            DOMAIN,
            UPLOAD_SERVICE,
            {
                CONF_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                CONF_FILENAME: TEST_FILENAME,
                CONF_DESTINATION_FOLDER: DESINATION_FOLDER,
            },
            blocking=True,
            return_response=True,
        )
