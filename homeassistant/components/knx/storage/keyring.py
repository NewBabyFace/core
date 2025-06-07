"""KNX Keyring handler."""

import logging
from pathlib import Path
import shutil
from typing import Final

from xknx.exceptions.exception import InvalidSecureConfiguration
from xknx.secure.keyring import Keyring, sync_load_keyring

from menuai.components.file_upload import process_uploaded_file
from menuai.core import menuai
from menuai.helpers.storage import STORAGE_DIR

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


DEFAULT_KNX_KEYRING_FILENAME: Final = "keyring.knxkeys"


async def save_uploaded_knxkeys_file(
    menuai: menuai, uploaded_file_id: str, password: str
) -> Keyring:
    """Validate the uploaded file and move it to the storage directory.

    Return a Keyring object.
    Raises InvalidSecureConfiguration if the file or password is invalid.
    """

    def _process_upload() -> Keyring:
        with process_uploaded_file(menuai, uploaded_file_id) as file_path:
            try:
                keyring = sync_load_keyring(
                    path=file_path,
                    password=password,
                )
            except InvalidSecureConfiguration as err:
                _LOGGER.debug(err)
                raise
            dest_path = Path(menuai.config.path(STORAGE_DIR, DOMAIN))
            dest_path.mkdir(exist_ok=True)
            dest_file = dest_path / DEFAULT_KNX_KEYRING_FILENAME
            shutil.move(file_path, dest_file)
        return keyring

    return await menuai.async_add_executor_job(_process_upload)
