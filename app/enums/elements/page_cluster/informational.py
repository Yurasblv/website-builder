from enum import StrEnum

from app.enums.base import BaseStrEnum
from app.enums.elements.base import BaseComplexElement


class InformationalElementType(BaseStrEnum):
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
    SOCIAL = "SOCIAL"  # Used for social links buttons
    AUTHOR = "AUTHOR"
    HEAD_CONTENT = "HEAD_CONTENT"
    IMG = "IMG"
    QUIZ = "QUIZ"
    GRAPH = "GRAPH"
    H2 = "H2"
    FAQ = "FAQ"
    TABLE = "TABLE"
    FACTS = "FACTS"
    CTA = "CTA"
    NEWS_BUBBLE = "NEWS_BUBBLE"
    REFERENCES = "REFERENCES"
    RELATED_PAGES = "RELATED_PAGES"
    CONTACTS = "CONTACTS"
    SHARE_BUTTON = "SHARE_BUTTON"
    COMMENT_FORM = "COMMENT_FORM"
    COMMENT_SECTION = "COMMENT_SECTION"

    @classmethod
    def h2_injection_elements(cls) -> list[StrEnum]:
        return [cls.IMG, cls.QUIZ, cls.GRAPH, cls.FAQ, cls.TABLE, cls.FACTS, cls.NEWS_BUBBLE, cls.CTA]

    @classmethod
    def elements_not_for_style_edit(cls) -> list[StrEnum]:
        return [cls.HEAD_CONTENT, cls.H2, cls.TITLE, cls.META_WORDS, cls.META_DESCRIPTION, cls.H1]


class InformationalTagType(BaseStrEnum):
    """
    Using in ElementContent schema for mark child tag in children list.
    """

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


class InformationalCTATags(BaseComplexElement):
    __head__ = CTA = "CTA"

    CTA_HEADING_TEXT = "CTA_HEADING_TEXT"
    CTA_DESCRIPTION_TEXT = "CTA_DESCRIPTION_TEXT"
    CTA_BUTTON = "CTA_BUTTON"
    CTA_IMG = "CTA_IMG"
    CTA_FIGCAPTION = "CTA_FIGCAPTION"


class InformationalContactTags(BaseComplexElement):
    __head__ = CONTACTS = "CONTACTS"
    CONTACT_BUTTON = "CONTACT_BUTTON"
    CONTACT_PHONE_NUMBER = "CONTACT_PHONE_NUMBER"
    CONTACT_EMAIL = "CONTACT_EMAIL"
    CONTACT_ADDRESS = "CONTACT_ADDRESS"
