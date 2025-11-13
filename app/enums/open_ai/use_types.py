from typing import Union

from .commercial_prompts import CommercialPagePrompt
from .formatting import FormattingPrompts
from .humanization import HumanizationPrompts
from .image import ImagePrompts
from .open_ai import ElementPrompts
from .structure import StructurePrompts

OpenAIPromptType = Union[
    ElementPrompts,
    CommercialPagePrompt,
    FormattingPrompts,
    StructurePrompts,
    ImagePrompts,
    HumanizationPrompts,
]
