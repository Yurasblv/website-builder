from enum import StrEnum


class BaseComplexElement(StrEnum):
    """
    Base class for complex elements, such as CTA, CONTACTS, GRIDS, etc.
    """

    __head__: str = "HEAD"

    @classmethod
    def list(cls, headless: bool = True) -> list:
        values = list(cls)
        head_value = getattr(cls, "__head__", None)

        if headless and head_value:
            values = [v for v in values if v != head_value]

        return values
