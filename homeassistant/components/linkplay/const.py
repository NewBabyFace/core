"""LinkPlay constants."""

from dataclasses import dataclass

from linkplay.controller import LinkPlayController

from menuai.const import Platform
from menuai.util.menuai_dict import menuaiKey


@dataclass
class LinkPlaySharedData:
    """Shared data for LinkPlay."""

    controller: LinkPlayController
    entity_to_bridge: dict[str, str]


DOMAIN = "linkplay"
SHARED_DATA = "shared_data"
SHARED_DATA_KEY: menuaiKey[LinkPlaySharedData] = menuaiKey(SHARED_DATA)
PLATFORMS = [Platform.BUTTON, Platform.MEDIA_PLAYER]
DATA_SESSION = "session"
