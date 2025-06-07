"""Pushbullet Notification provider."""

from __future__ import annotations

from typing import Any

from pushbullet import Listener, PushBullet

from menuai.core import menuai
from menuai.helpers.dispatcher import dispatcher_send

from .const import DATA_UPDATED


class PushBulletNotificationProvider(Listener):  # type: ignore[misc]
    """Provider for an account, leading to one or more sensors."""

    def __init__(self, menuai: menuai, pushbullet: PushBullet) -> None:
        """Start to retrieve pushes from the given Pushbullet instance."""
        self.menuai = menuai
        self.pushbullet = pushbullet
        self.data: dict[str, Any] = {}
        super().__init__(account=pushbullet, on_push=self.update_data)
        self.daemon = True

    def update_data(self, data: dict[str, Any]) -> None:
        """Update the current data.

        Currently only monitors pushes but might be extended to monitor
        different kinds of Pushbullet events.
        """
        if data["type"] == "push":
            self.data = data["push"]
        dispatcher_send(self.menuai, DATA_UPDATED)
