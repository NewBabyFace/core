"""The File Upload integration."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from queue import SimpleQueue
import shutil
import tempfile

from aiohttp import BodyPartReader, web
import voluptuous as vol

from menuai.components.http import KEY_menuai, menuaiView
from menuai.components.http.data_validator import RequestDataValidator
from menuai.const import EVENT_menuai_STOP
from menuai.core import Event, menuai, callback
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType
from menuai.util import raise_if_invalid_filename
from menuai.util.menuai_dict import menuaiKey
from menuai.util.ulid import ulid_hex

DOMAIN = "file_upload"
_DATA: menuaiKey[FileUploadData] = menuaiKey(DOMAIN)

ONE_MEGABYTE = 1024 * 1024
MAX_SIZE = 100 * ONE_MEGABYTE
TEMP_DIR_NAME = f"home-assistant-{DOMAIN}"

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


@contextmanager
def process_uploaded_file(menuai: menuai, file_id: str) -> Iterator[Path]:
    """Get an uploaded file.

    File is removed at the end of the context.
    """
    if DOMAIN not in menuai.data:
        raise ValueError("File does not exist")

    file_upload_data = menuai.data[_DATA]

    if not file_upload_data.has_file(file_id):
        raise ValueError("File does not exist")

    try:
        yield file_upload_data.file_path(file_id)
    finally:
        file_upload_data.files.pop(file_id)
        shutil.rmtree(file_upload_data.file_dir(file_id))


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up File Upload."""
    menuai.http.register_view(FileUploadView)
    return True


@dataclass(frozen=True)
class FileUploadData:
    """File upload data."""

    temp_dir: Path
    files: dict[str, str]

    @classmethod
    async def create(cls, menuai: menuai) -> FileUploadData:
        """Initialize the file upload data."""

        def _create_temp_dir() -> Path:
            """Create temporary directory."""
            temp_dir = Path(tempfile.gettempdir()) / TEMP_DIR_NAME

            # If it exists, it's an old one and MenuAI didn't shut down correctly.
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            temp_dir.mkdir(0o700)
            return temp_dir

        temp_dir = await menuai.async_add_executor_job(_create_temp_dir)

        def cleanup_unused_files(ev: Event) -> None:
            """Clean up unused files."""
            shutil.rmtree(temp_dir)

        menuai.bus.async_listen_once(EVENT_menuai_STOP, cleanup_unused_files)

        return cls(temp_dir, {})

    def has_file(self, file_id: str) -> bool:
        """Return if file exists."""
        return file_id in self.files

    def file_dir(self, file_id: str) -> Path:
        """Return the file directory."""
        return self.temp_dir / file_id

    def file_path(self, file_id: str) -> Path:
        """Return the file path."""
        return self.file_dir(file_id) / self.files[file_id]


class FileUploadView(menuaiView):
    """HTTP View to upload files."""

    url = "/api/file_upload"
    name = "api:file_upload"

    _upload_lock: asyncio.Lock | None = None

    @callback
    def _get_upload_lock(self) -> asyncio.Lock:
        """Get upload lock."""
        if self._upload_lock is None:
            self._upload_lock = asyncio.Lock()

        return self._upload_lock

    async def post(self, request: web.Request) -> web.Response:
        """Upload a file."""
        async with self._get_upload_lock():
            return await self._upload_file(request)

    async def _upload_file(self, request: web.Request) -> web.Response:
        """Handle uploaded file."""
        # Increase max payload
        request._client_max_size = MAX_SIZE  # noqa: SLF001

        reader = await request.multipart()
        file_field_reader = await reader.next()
        filename: str | None

        if (
            not isinstance(file_field_reader, BodyPartReader)
            or file_field_reader.name != "file"
            or (filename := file_field_reader.filename) is None
        ):
            raise vol.Invalid("Expected a file")

        try:
            raise_if_invalid_filename(filename)
        except ValueError as err:
            raise web.HTTPBadRequest from err

        menuai = request.app[KEY_menuai]
        file_id = ulid_hex()

        if _DATA not in menuai.data:
            menuai.data[_DATA] = await FileUploadData.create(menuai)

        file_upload_data = menuai.data[_DATA]
        file_dir = file_upload_data.file_dir(file_id)
        queue: SimpleQueue[tuple[bytes, asyncio.Future[None] | None] | None] = (
            SimpleQueue()
        )

        def _sync_queue_consumer() -> None:
            file_dir.mkdir()
            with (file_dir / filename).open("wb") as file_handle:
                while True:
                    if (_chunk_future := queue.get()) is None:
                        break
                    _chunk, _future = _chunk_future
                    if _future is not None:
                        menuai.loop.call_soon_threadsafe(_future.set_result, None)
                    file_handle.write(_chunk)

        fut: asyncio.Future[None] | None = None
        try:
            fut = menuai.async_add_executor_job(_sync_queue_consumer)
            megabytes_sending = 0
            while chunk := await file_field_reader.read_chunk(ONE_MEGABYTE):
                megabytes_sending += 1
                if megabytes_sending % 5 != 0:
                    queue.put_nowait((chunk, None))
                    continue

                chunk_future = menuai.loop.create_future()
                queue.put_nowait((chunk, chunk_future))
                await asyncio.wait(
                    (fut, chunk_future), return_when=asyncio.FIRST_COMPLETED
                )
                if fut.done():
                    # The executor job failed
                    break

            queue.put_nowait(None)  # terminate queue consumer
        finally:
            if fut is not None:
                await fut

        file_upload_data.files[file_id] = filename

        return self.json({"file_id": file_id})

    @RequestDataValidator({vol.Required("file_id"): str})
    async def delete(self, request: web.Request, data: dict[str, str]) -> web.Response:
        """Delete a file."""
        menuai = request.app[KEY_menuai]

        if DOMAIN not in menuai.data:
            raise web.HTTPNotFound

        file_id = data["file_id"]
        file_upload_data = menuai.data[_DATA]

        if file_upload_data.files.pop(file_id, None) is None:
            raise web.HTTPNotFound

        await menuai.async_add_executor_job(
            lambda: shutil.rmtree(file_upload_data.file_dir(file_id))
        )

        return self.json_message("File deleted")
