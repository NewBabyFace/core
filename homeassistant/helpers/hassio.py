"""menuai.io helper."""

import os

from menuai.core import menuai, callback


@callback
def is_menuaiio(menuai: menuai) -> bool:
    """Return true if menuai.io is loaded.

    Async friendly.
    """
    return "menuaiio" in menuai.config.components


@callback
def get_supervisor_ip() -> str | None:
    """Return the supervisor ip address."""
    if "SUPERVISOR" not in os.environ:
        return None
    return os.environ["SUPERVISOR"].partition(":")[0]
