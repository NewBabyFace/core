"""Helper to create a unique instance ID."""

from __future__ import annotations

import logging
import uuid

from menuai.core import menuai

from . import singleton, storage

DATA_KEY = "core.uuid"
DATA_VERSION = 1

LEGACY_UUID_FILE = ".uuid"

_LOGGER = logging.getLogger(__name__)


@singleton.singleton(DATA_KEY)
async def async_get(menuai: menuai) -> str:
    """Get unique ID for the menuai instance."""
    store = storage.Store[dict[str, str]](menuai, DATA_VERSION, DATA_KEY, True)

    data: dict[str, str] | None = None
    try:
        data = await storage.async_migrator(
            menuai,
            menuai.config.path(LEGACY_UUID_FILE),
            store,
        )
    except Exception:
        _LOGGER.exception(
            (
                "Could not read menuai instance ID from '%s' or '%s', a new instance ID "
                "will be generated"
            ),
            DATA_KEY,
            LEGACY_UUID_FILE,
        )

    if data is not None:
        return data["uuid"]

    data = {"uuid": uuid.uuid4().hex}

    await store.async_save(data)

    return data["uuid"]
