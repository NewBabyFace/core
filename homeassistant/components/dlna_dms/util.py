"""Small utility functions for the dlna_dms integration."""

from __future__ import annotations

from menuai.core import menuai
from menuai.util import slugify

from .const import CONF_SOURCE_ID, DOMAIN


def generate_source_id(menuai: menuai, name: str) -> str:
    """Generate a unique source ID."""
    other_entries = menuai.config_entries.async_entries(DOMAIN)
    other_source_ids: set[str] = {
        other_source_id
        for entry in other_entries
        if (other_source_id := entry.data.get(CONF_SOURCE_ID))
    }

    source_id_base = slugify(name)
    if source_id_base not in other_source_ids:
        return source_id_base

    tries = 1
    while (suggested_source_id := f"{source_id_base}_{tries}") in other_source_ids:
        tries += 1

    return suggested_source_id
