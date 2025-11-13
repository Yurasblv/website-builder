from typing import Union

from .commercial import (
    Commercial1CTATags,
    Commercial1ElementType,
    Commercial1InnerCTATags,
    Commercial1TagType,
    Commercial2ElementType,
    Commercial2TagType,
)
from .informational import (
    InformationalContactTags,
    InformationalCTATags,
    InformationalElementType,
    InformationalTagType,
)
from .navigational import NavigationalElementType, NavigationalTagType

InformationalPageElementType = Union[
    InformationalElementType, InformationalTagType, InformationalCTATags, InformationalContactTags
]

Commercial1PageElementType = Union[
    Commercial1ElementType, Commercial1TagType, Commercial1CTATags, Commercial1InnerCTATags
]

Commercial2PageElementType = Union[Commercial2ElementType, Commercial2TagType]

NavigationalPageElementType = Union[NavigationalTagType, NavigationalElementType]

PageElementType = Union[
    InformationalPageElementType, Commercial1PageElementType, Commercial2PageElementType, NavigationalPageElementType
]
