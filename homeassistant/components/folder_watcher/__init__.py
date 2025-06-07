"""Component for monitoring activity on a folder."""

from __future__ import annotations

import logging
import os
from typing import cast

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileClosedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
    FileSystemMovedEvent,
    PatternMatchingEventHandler,
)
from watchdog.observers import Observer

from menuai.config_entries import ConfigEntry
from menuai.const import EVENT_menuai_START, EVENT_menuai_STOP
from menuai.core import Event, menuai
from menuai.helpers.dispatcher import dispatcher_send
from menuai.helpers.issue_registry import IssueSeverity, async_create_issue

from .const import CONF_FOLDER, CONF_PATTERNS, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Folder watcher from a config entry."""

    path: str = entry.options[CONF_FOLDER]
    patterns: list[str] = entry.options[CONF_PATTERNS]
    if not menuai.config.is_allowed_path(path):
        _LOGGER.error("Folder %s is not valid or allowed", path)
        async_create_issue(
            menuai,
            DOMAIN,
            f"setup_not_allowed_path_{path}",
            is_fixable=False,
            is_persistent=False,
            severity=IssueSeverity.ERROR,
            translation_key="setup_not_allowed_path",
            translation_placeholders={
                "path": path,
                "config_variable": "allowlist_external_dirs",
            },
            learn_more_url="https://www.home-assistant.io/docs/configuration/basic/#allowlist_external_dirs",
        )
        return False
    await menuai.async_add_executor_job(Watcher, path, patterns, menuai, entry.entry_id)
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def create_event_handler(
    patterns: list[str], menuai: menuai, entry_id: str
) -> EventHandler:
    """Return the Watchdog EventHandler object."""
    return EventHandler(patterns, menuai, entry_id)


class EventHandler(PatternMatchingEventHandler):
    """Class for handling Watcher events."""

    def __init__(self, patterns: list[str], menuai: menuai, entry_id: str) -> None:
        """Initialise the EventHandler."""
        super().__init__(patterns=patterns)
        self.menuai = menuai
        self.entry_id = entry_id

    def process(self, event: FileSystemEvent, moved: bool = False) -> None:
        """On Watcher event, fire HA event."""
        _LOGGER.debug("process(%s)", event)
        if not event.is_directory:
            folder, file_name = os.path.split(event.src_path)
            fireable = {
                "event_type": event.event_type,
                "path": event.src_path,
                "file": file_name,
                "folder": folder,
            }

            _extra = {}
            if moved:
                event = cast(FileSystemMovedEvent, event)
                dest_folder, dest_file_name = os.path.split(event.dest_path)
                _extra = {
                    "dest_path": event.dest_path,
                    "dest_file": dest_file_name,
                    "dest_folder": dest_folder,
                }
                fireable.update(_extra)
            self.menuai.bus.fire(
                DOMAIN,
                fireable,
            )
            signal = f"folder_watcher-{self.entry_id}"
            dispatcher_send(self.menuai, signal, event.event_type, fireable)

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        """File modified."""
        self.process(event)

    def on_moved(self, event: DirMovedEvent | FileMovedEvent) -> None:
        """File moved."""
        self.process(event, moved=True)

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent) -> None:
        """File created."""
        self.process(event)

    def on_deleted(self, event: DirDeletedEvent | FileDeletedEvent) -> None:
        """File deleted."""
        self.process(event)

    def on_closed(self, event: FileClosedEvent) -> None:
        """File closed."""
        self.process(event)


class Watcher:
    """Class for starting Watchdog."""

    def __init__(
        self, path: str, patterns: list[str], menuai: menuai, entry_id: str
    ) -> None:
        """Initialise the watchdog observer."""
        self._observer = Observer()
        self._observer.schedule(
            create_event_handler(patterns, menuai, entry_id), path, recursive=True
        )
        if not menuai.is_running:
            menuai.bus.listen_once(EVENT_menuai_START, self.startup)
        else:
            self.startup(None)
        menuai.bus.listen_once(EVENT_menuai_STOP, self.shutdown)

    def startup(self, event: Event | None) -> None:
        """Start the watcher."""
        self._observer.start()

    def shutdown(self, event: Event | None) -> None:
        """Shutdown the watcher."""
        self._observer.stop()
        self._observer.join()
