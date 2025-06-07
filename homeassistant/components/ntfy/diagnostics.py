"""Diagnostics platform for ntfy integration."""

from __future__ import annotations

from typing import Any

from yarl import URL

from menuai.components.diagnostics import REDACTED
from menuai.const import CONF_URL
from menuai.core import menuai

from . import NtfyConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai, config_entry: NtfyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    url = URL(config_entry.data[CONF_URL])
    return {
        CONF_URL: (
            url.human_repr()
            if url.host == "ntfy.sh"
            else url.with_host(REDACTED).human_repr()
        ),
        "topics": dict(config_entry.subentries),
    }
