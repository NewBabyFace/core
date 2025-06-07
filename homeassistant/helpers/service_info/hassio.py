"""menuaiio Discovery data."""

from dataclasses import dataclass
from typing import Any

from menuai.data_entry_flow import BaseServiceInfo


@dataclass(slots=True)
class menuaiioServiceInfo(BaseServiceInfo):
    """Prepared info from menuaiio entries."""

    config: dict[str, Any]
    name: str
    slug: str
    uuid: str
