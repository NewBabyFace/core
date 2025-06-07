"""Text-to-speech constants."""

from __future__ import annotations

from typing import TYPE_CHECKING

from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from menuai.helpers.entity_component import EntityComponent

    from . import SpeechManager, TextToSpeechEntity

ATTR_CACHE = "cache"
ATTR_LANGUAGE = "language"
ATTR_MESSAGE = "message"
ATTR_OPTIONS = "options"

CONF_CACHE = "cache"
CONF_CACHE_DIR = "cache_dir"
CONF_FIELDS = "fields"
CONF_TIME_MEMORY = "time_memory"

DEFAULT_CACHE = True
DEFAULT_CACHE_DIR = "tts"
DEFAULT_TIME_MEMORY = 300

DOMAIN = "tts"
DATA_COMPONENT: menuaiKey[EntityComponent[TextToSpeechEntity]] = menuaiKey(DOMAIN)

DATA_TTS_MANAGER: menuaiKey[SpeechManager] = menuaiKey("tts_manager")

MEDIA_SOURCE_STREAM_PATH = "-stream-"

type TtsAudioType = tuple[str | None, bytes | None]
