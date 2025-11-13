from typing import Awaitable, Callable

from app.schemas.elements import ElementContent
from app.schemas.page.cluster_page import ClusterPageCreate
from app.schemas.xmindmap import XMindmapBase

ContentStructure = dict[str, ElementContent]
PageFuncType = Callable[[list[XMindmapBase]], Awaitable[list[ClusterPageCreate]]]
