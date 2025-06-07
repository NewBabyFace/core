"""Signal handling related helpers."""

import asyncio
import logging
import signal

from menuai.const import RESTART_EXIT_CODE
from menuai.core import menuai, callback
from menuai.loader import bind_menuai
from menuai.util.menuai_dict import menuaiKey

_LOGGER = logging.getLogger(__name__)

KEY_HA_STOP: menuaiKey[asyncio.Task[None]] = menuaiKey("menuai_stop")


@callback
@bind_menuai
def async_register_signal_handling(menuai: menuai) -> None:
    """Register system signal handler for core."""

    @callback
    def async_signal_handle(exit_code: int) -> None:
        """Wrap signal handling.

        * queue call to shutdown task
        * re-instate default handler
        """
        menuai.loop.remove_signal_handler(signal.SIGTERM)
        menuai.loop.remove_signal_handler(signal.SIGINT)
        menuai.data[KEY_HA_STOP] = asyncio.create_task(menuai.async_stop(exit_code))

    try:
        menuai.loop.add_signal_handler(signal.SIGTERM, async_signal_handle, 0)
    except ValueError:
        _LOGGER.warning("Could not bind to SIGTERM")

    try:
        menuai.loop.add_signal_handler(signal.SIGINT, async_signal_handle, 0)
    except ValueError:
        _LOGGER.warning("Could not bind to SIGINT")

    try:
        menuai.loop.add_signal_handler(
            signal.SIGHUP, async_signal_handle, RESTART_EXIT_CODE
        )
    except ValueError:
        _LOGGER.warning("Could not bind to SIGHUP")
