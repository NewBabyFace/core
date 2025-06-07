"""Shared constants for script and automation tracing and debugging."""

from __future__ import annotations

from typing import TYPE_CHECKING

from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from menuai.helpers.storage import Store

    from .models import TraceData


CONF_STORED_TRACES = "stored_traces"
DATA_TRACE: menuaiKey[TraceData] = menuaiKey("trace")
DATA_TRACE_STORE: menuaiKey[Store[dict[str, list]]] = menuaiKey("trace_store")
DATA_TRACES_RESTORED: menuaiKey[bool] = menuaiKey("trace_traces_restored")
DEFAULT_STORED_TRACES = 5  # Stored traces per script or automation
