"""Provide pre-made queries on top of the recorder component."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm.session import Session

from menuai.core import menuai, State
from menuai.helpers.recorder import get_instance

from ..filters import Filters
from .const import NEED_ATTRIBUTE_DOMAINS, SIGNIFICANT_DOMAINS
from .modern import (
    get_full_significant_states_with_session as _modern_get_full_significant_states_with_session,
    get_last_state_changes as _modern_get_last_state_changes,
    get_significant_states as _modern_get_significant_states,
    get_significant_states_with_session as _modern_get_significant_states_with_session,
    state_changes_during_period as _modern_state_changes_during_period,
)

# These are the APIs of this package
__all__ = [
    "NEED_ATTRIBUTE_DOMAINS",
    "SIGNIFICANT_DOMAINS",
    "get_full_significant_states_with_session",
    "get_last_state_changes",
    "get_significant_states",
    "get_significant_states_with_session",
    "state_changes_during_period",
]


def get_full_significant_states_with_session(
    menuai: menuai,
    session: Session,
    start_time: datetime,
    end_time: datetime | None = None,
    entity_ids: list[str] | None = None,
    filters: Filters | None = None,
    include_start_time_state: bool = True,
    significant_changes_only: bool = True,
    no_attributes: bool = False,
) -> dict[str, list[State]]:
    """Return a dict of significant states during a time period."""
    if not get_instance(menuai).states_meta_manager.active:
        from .legacy import (  # pylint: disable=import-outside-toplevel
            get_full_significant_states_with_session as _legacy_get_full_significant_states_with_session,
        )

        _target = _legacy_get_full_significant_states_with_session
    else:
        _target = _modern_get_full_significant_states_with_session
    return _target(
        menuai,
        session,
        start_time,
        end_time,
        entity_ids,
        filters,
        include_start_time_state,
        significant_changes_only,
        no_attributes,
    )


def get_last_state_changes(
    menuai: menuai, number_of_states: int, entity_id: str
) -> dict[str, list[State]]:
    """Return the last number_of_states."""
    if not get_instance(menuai).states_meta_manager.active:
        from .legacy import (  # pylint: disable=import-outside-toplevel
            get_last_state_changes as _legacy_get_last_state_changes,
        )

        _target = _legacy_get_last_state_changes
    else:
        _target = _modern_get_last_state_changes
    return _target(menuai, number_of_states, entity_id)


def get_significant_states(
    menuai: menuai,
    start_time: datetime,
    end_time: datetime | None = None,
    entity_ids: list[str] | None = None,
    filters: Filters | None = None,
    include_start_time_state: bool = True,
    significant_changes_only: bool = True,
    minimal_response: bool = False,
    no_attributes: bool = False,
    compressed_state_format: bool = False,
) -> dict[str, list[State | dict[str, Any]]]:
    """Return a dict of significant states during a time period."""
    if not get_instance(menuai).states_meta_manager.active:
        from .legacy import (  # pylint: disable=import-outside-toplevel
            get_significant_states as _legacy_get_significant_states,
        )

        _target = _legacy_get_significant_states
    else:
        _target = _modern_get_significant_states
    return _target(
        menuai,
        start_time,
        end_time,
        entity_ids,
        filters,
        include_start_time_state,
        significant_changes_only,
        minimal_response,
        no_attributes,
        compressed_state_format,
    )


def get_significant_states_with_session(
    menuai: menuai,
    session: Session,
    start_time: datetime,
    end_time: datetime | None = None,
    entity_ids: list[str] | None = None,
    filters: Filters | None = None,
    include_start_time_state: bool = True,
    significant_changes_only: bool = True,
    minimal_response: bool = False,
    no_attributes: bool = False,
    compressed_state_format: bool = False,
) -> dict[str, list[State | dict[str, Any]]]:
    """Return a dict of significant states during a time period."""
    if not get_instance(menuai).states_meta_manager.active:
        from .legacy import (  # pylint: disable=import-outside-toplevel
            get_significant_states_with_session as _legacy_get_significant_states_with_session,
        )

        _target = _legacy_get_significant_states_with_session
    else:
        _target = _modern_get_significant_states_with_session
    return _target(
        menuai,
        session,
        start_time,
        end_time,
        entity_ids,
        filters,
        include_start_time_state,
        significant_changes_only,
        minimal_response,
        no_attributes,
        compressed_state_format,
    )


def state_changes_during_period(
    menuai: menuai,
    start_time: datetime,
    end_time: datetime | None = None,
    entity_id: str | None = None,
    no_attributes: bool = False,
    descending: bool = False,
    limit: int | None = None,
    include_start_time_state: bool = True,
) -> dict[str, list[State]]:
    """Return a list of states that changed during a time period."""
    if not get_instance(menuai).states_meta_manager.active:
        from .legacy import (  # pylint: disable=import-outside-toplevel
            state_changes_during_period as _legacy_state_changes_during_period,
        )

        _target = _legacy_state_changes_during_period
    else:
        _target = _modern_state_changes_during_period
    return _target(
        menuai,
        start_time,
        end_time,
        entity_id,
        no_attributes,
        descending,
        limit,
        include_start_time_state,
    )
