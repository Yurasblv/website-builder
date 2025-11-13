from app.enums.base import BaseStrEnum
from app.enums.elements.base import BaseComplexElement


class Commercial1ElementType(BaseStrEnum):
    """
    Using in ElementContent schema for mark parent tag.
    """

    TITLE = "TITLE"
    META_WORDS = "META_WORDS"
    META_DESCRIPTION = "META_DESCRIPTION"
    META_BACKLINK = "META_BACKLINK"
    H1 = "H1"
    CONTENT_MENU = "CONTENT_MENU"
    PROGRESS_BAR = "PROGRESS_BAR"
    CTA = "CTA"
    FEATURES = "FEATURES"
    BENEFITS = "BENEFITS"
    GRID = "GRID"
    INNER_CTA = "INNER_CTA"
    FAQ = "FAQ"
    RELATED_PAGES = "RELATED_PAGES"

    @classmethod
    def queue(cls) -> tuple["Commercial1ElementType", ...]:
        return (
            cls.TITLE,
            cls.META_WORDS,
            cls.META_DESCRIPTION,
            cls.H1,
            cls.CONTENT_MENU,
            cls.PROGRESS_BAR,
            cls.CTA,
            cls.FEATURES,
            cls.BENEFITS,
            cls.GRID,
            cls.INNER_CTA,
            cls.FAQ,
            cls.RELATED_PAGES,
        )


class Commercial1TagType(BaseStrEnum):
    """
    Using in ElementContent schema for mark child tag in children list.
    """

    H2 = "H2"
    CARD = "CARD"
    IMG = "IMG"
    DIV = "DIV"
    FIGCAPTION = "FIGCAPTION"
    A = "A"
    P = "P"
    UPPER_RELATION = "UPPER_RELATION"
    INNER_RELATION = "INNER_RELATION"
    LOWER_RELATION = "LOWER_RELATION"


class Commercial1CTATags(BaseComplexElement):
    __head__ = CTA = "CTA"

    CTA_HEADING_TEXT = "CTA_HEADING_TEXT"
    CTA_DESCRIPTION_TEXT = "CTA_DESCRIPTION_TEXT"
    CTA_BUTTON = "CTA_BUTTON"
    CTA_IMG = "CTA_IMG"


class Commercial1InnerCTATags(BaseComplexElement):
    __head__ = INNER_CTA = "INNER_CTA"

    INNER_CTA_HEADING_TEXT = "INNER_CTA_HEADING_TEXT"
    INNER_CTA_BUTTON = "INNER_CTA_BUTTON"


class Commercial2ElementType(BaseStrEnum):
    """
    Using in ElementContent schema for mark parent tag.
    """

    TITLE = "TITLE"
    META_WORDS = "META_WORDS"
    META_DESCRIPTION = "META_DESCRIPTION"
    H1 = "H1"
    CTA = "CTA"
    GRID = "GRID"
    H2 = "H2"
    INNER_CTA = "INNER_CTA"
    CUSTOMER_RATING = "CUSTOMER_RATING"

    @classmethod
    def queue(cls) -> tuple["Commercial2ElementType", ...]:
        return (
            cls.TITLE,
            cls.META_WORDS,
            cls.META_DESCRIPTION,
            cls.H1,
            cls.CTA,
            cls.GRID,
            cls.H2,
            cls.INNER_CTA,
            cls.CUSTOMER_RATING,
        )


class Commercial2TagType(BaseStrEnum):
    """
    Using in ElementContent schema for mark child tag in children list.
    """

    CARD = "CARD"
    DIV = "DIV"
    FIGCAPTION = "FIGCAPTION"
    A = "A"
    P = "P"
    UPPER_RELATION = "UPPER_RELATION"
    INNER_RELATION = "INNER_RELATION"
    LOWER_RELATION = "LOWER_RELATION"


class Commercial2CTATags(BaseComplexElement):
    __head__ = CTA = "CTA"

    CTA_HEADING_TEXT = "CTA_HEADING_TEXT"
    CTA_DESCRIPTION_TEXT = "CTA_DESCRIPTION_TEXT"
    CTA_BUTTON = "CTA_BUTTON"
    CTA_IMG = "CTA_IMG"
