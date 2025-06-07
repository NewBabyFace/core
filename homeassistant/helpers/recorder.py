"""Helpers to check recorder."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
import functools
import logging
from typing import TYPE_CHECKING, Any

from menuai.core import menuai, callback
from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from sqlalchemy.orm.session import Session

    from menuai.components.recorder import Recorder

_LOGGER = logging.getLogger(__name__)

DATA_RECORDER: menuaiKey[RecorderData] = menuaiKey("recorder")
DATA_INSTANCE: menuaiKey[Recorder] = menuaiKey("recorder_instance")


@dataclass(slots=True)
class RecorderData:
    """Recorder data stored in menuai.data."""

    recorder_platforms: dict[str, Any] = field(default_factory=dict)
    db_connected: asyncio.Future[bool] = field(default_factory=asyncio.Future)


@callback
def async_migration_in_progress(menuai: menuai) -> bool:
    """Check to see if a recorder migration is in progress."""
    # pylint: disable-next=import-outside-toplevel
    from menuai.components import recorder

    return recorder.util.async_migration_in_progress(menuai)


@callback
def async_migration_is_live(menuai: menuai) -> bool:
    """Check to see if a recorder migration is live."""
    # pylint: disable-next=import-outside-toplevel
    from menuai.components import recorder

    return recorder.util.async_migration_is_live(menuai)


@callback
def async_initialize_recorder(menuai: menuai) -> None:
    """Initialize recorder data.

    This creates the RecorderData instance stored in menuai.data[DATA_RECORDER] and
    registers the basic recorder websocket API which is used by frontend to determine
    if the recorder is migrating the database.
    """
    # pylint: disable-next=import-outside-toplevel
    from menuai.components.recorder.basic_websocket_api import async_setup

    menuai.data[DATA_RECORDER] = RecorderData()
    async_setup(menuai)


@functools.lru_cache(maxsize=1)
def get_instance(menuai: menuai) -> Recorder:
    """Get the recorder instance."""
    return menuai.data[DATA_INSTANCE]


@contextmanager
def session_scope(
    *,
    menuai: menuai | None = None,
    session: Session | None = None,
    exception_filter: Callable[[Exception], bool] | None = None,
    read_only: bool = False,
) -> Generator[Session]:
    """Provide a transactional scope around a series of operations.

    read_only is used to indicate that the session is only used for reading
    data and that no commit is required. It does not prevent the session
    from writing and is not a security measure.
    """
    if session is None and menuai is not None:
        session = get_instance(menuai).get_session()

    if session is None:
        raise RuntimeError("Session required")

    need_rollback = False
    try:
        yield session
        if not read_only and session.get_transaction():
            need_rollback = True
            session.commit()
    except Exception as err:
        _LOGGER.exception("Error executing query")
        if need_rollback:
            session.rollback()
        if not exception_filter or not exception_filter(err):
            raise
    finally:
        session.close()
