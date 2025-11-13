from app.enums.base import BaseStrEnum


class NavigationalElementType(BaseStrEnum):
    """
    Using in ElementContent schema for mark parent tag.
    """

    TITLE = "TITLE"
    META_WORDS = "META_WORDS"
    META_DESCRIPTION = "META_DESCRIPTION"
    META_BACKLINK = "META_BACKLINK"
    H1 = "H1"
    PROGRESS_BAR = "PROGRESS_BAR"
    AUTHOR = "AUTHOR"
    HEAD_CONTENT = "HEAD_CONTENT"
    TABLE_FIRST = "TABLE_FIRST"
    IMG_FIRST = "IMG_FIRST"
    IMG_SECOND = "IMG_SECOND"
    IMG_THIRD = "IMG_THIRD"
    TABLE_SECOND = "TABLE_SECOND"
    NEWS_BUBBLE = "NEWS_BUBBLE"
    REFERENCES = "REFERENCES"

    @classmethod
    def h2_injection_elements(cls) -> tuple["NavigationalElementType", ...]:
        return (
            cls.IMG_FIRST,
            cls.IMG_SECOND,
            cls.IMG_THIRD,
            cls.TABLE_FIRST,
            cls.TABLE_SECOND,
        )


class NavigationalTagType(BaseStrEnum):
    """
    Using in ElementContent schema for mark child tag in children list.
    """

    H2 = "H2"
    DIV = "DIV"
    FIGCAPTION = "FIGCAPTION"
    A = "A"
    P = "P"
    STRONG = "STRONG"
    SPAN = "SPAN"
    LABEL = "LABEL"
    RADIO = "RADIO"
    UPPER_RELATION = "UPPER_RELATION"
    INNER_RELATION = "INNER_RELATION"
    LOWER_RELATION = "LOWER_RELATION"
