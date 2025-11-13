from dataclasses import dataclass

from app.enums import PageIntent
from app.enums.elements import (
    Commercial1CTATags,
    Commercial1ElementType,
    Commercial1InnerCTATags,
    InformationalContactTags,
    InformationalCTATags,
    InformationalElementType,
    NavigationalElementType,
)

from .base import BaseStyle, ElementSettings, ElementStyleParam


@dataclass(frozen=True)
class InformationalPageElementsParams:
    general_style_sample = BaseStyle(
        accentColor="#7792ff", backgroundColor="#ffffff", color="#000000", fontFamily="Roboto"
    )
    elements_param_sample = [
        ElementStyleParam(type=InformationalElementType.TITLE, position=0),
        ElementStyleParam(type=InformationalElementType.META_DESCRIPTION, position=1),
        ElementStyleParam(type=InformationalElementType.META_WORDS, position=2),
        ElementStyleParam(type=InformationalElementType.META_BACKLINK, position=3, enabled=False),
        ElementStyleParam(type=InformationalElementType.H1, position=4),
        ElementStyleParam(
            type=InformationalElementType.CONTENT_MENU,
            className="default",
            position=5,
            style=BaseStyle(backgroundColor="#ffffff", color="#000000"),
        ),
        ElementStyleParam(
            type=InformationalElementType.PROGRESS_BAR,
            className="default",
            position=6,
            style=BaseStyle(backgroundColor="#ffffff", color="#000000"),
        ),
        ElementStyleParam(
            type=InformationalElementType.SOCIAL,
            position=7,
        ),
        ElementStyleParam(
            type=InformationalElementType.AUTHOR,
            position=8,
        ),
        ElementStyleParam(type=InformationalElementType.HEAD_CONTENT, className="default", position=9),
        ElementStyleParam(type=InformationalElementType.IMG, className="default", position=10),
        ElementStyleParam(type=InformationalElementType.QUIZ, className="default", position=11),
        ElementStyleParam(
            type=InformationalElementType.GRAPH,
            className="default",
            settings=ElementSettings(graphVariant="doughnut"),
            position=12,
        ),
        ElementStyleParam(type=InformationalElementType.FAQ, className="default", position=13),
        ElementStyleParam(
            type=InformationalElementType.TABLE,
            className="default",
            style=BaseStyle(backgroundColor="#000000"),
            settings=ElementSettings(tableVariant="horizontal"),
            position=14,
        ),
        ElementStyleParam(type=InformationalElementType.FACTS, className="default", position=15),
        ElementStyleParam(type=InformationalCTATags.CTA, className="default", position=16, enabled=False),
        ElementStyleParam(type=InformationalCTATags.CTA_HEADING_TEXT, className="default", position=16, enabled=False),
        ElementStyleParam(
            type=InformationalCTATags.CTA_DESCRIPTION_TEXT, className="default", position=16, enabled=False
        ),
        ElementStyleParam(
            type=InformationalCTATags.CTA_BUTTON,
            className="default",
            style=BaseStyle(borderRadius="8px"),
            position=16,
            enabled=False,
        ),
        ElementStyleParam(type=InformationalCTATags.CTA_IMG, className="default", position=16, enabled=False),
        ElementStyleParam(type=InformationalCTATags.CTA_FIGCAPTION, className="default", position=16, enabled=False),
        ElementStyleParam(type=InformationalElementType.NEWS_BUBBLE, className="default", position=17),
        ElementStyleParam(
            type=InformationalElementType.REFERENCES,
            className="default",
            settings=ElementSettings(reference_follow=False),
            position=18,
        ),
        ElementStyleParam(type=InformationalElementType.RELATED_PAGES, className="default", position=19),
        ElementStyleParam(type=InformationalContactTags.CONTACTS, className="default", position=20),
        ElementStyleParam(type=InformationalContactTags.CONTACT_PHONE_NUMBER, position=20),
        ElementStyleParam(type=InformationalContactTags.CONTACT_EMAIL, position=20),
        ElementStyleParam(type=InformationalContactTags.CONTACT_ADDRESS, position=20),
        ElementStyleParam(
            type=InformationalContactTags.CONTACT_BUTTON,
            style=BaseStyle(border="solid", borderRadius="12px"),
            position=20,
        ),
        ElementStyleParam(type=InformationalElementType.SHARE_BUTTON, className="default", position=20),
        ElementStyleParam(type=InformationalElementType.COMMENT_FORM, className="default", position=21),
        ElementStyleParam(type=InformationalElementType.COMMENT_SECTION, className="default", position=22),
    ]


@dataclass(frozen=True)
class CommercialPageElementsParams:
    general_style_sample = BaseStyle(
        accentColor="#7792ff", backgroundColor="#ffffff", color="#000000", fontFamily="Roboto"
    )
    elements_param_sample = [
        ElementStyleParam(type=Commercial1ElementType.TITLE, position=0),
        ElementStyleParam(type=Commercial1ElementType.META_WORDS, position=1),
        ElementStyleParam(type=Commercial1ElementType.META_DESCRIPTION, position=2),
        ElementStyleParam(type=Commercial1ElementType.META_BACKLINK, position=3, enabled=False),
        ElementStyleParam(type=Commercial1ElementType.H1, position=4),
        ElementStyleParam(
            type=Commercial1ElementType.CONTENT_MENU,
            className="default",
            position=5,
            style=BaseStyle(backgroundColor="#ffffff", color="#000000"),
        ),
        ElementStyleParam(
            type=Commercial1ElementType.PROGRESS_BAR,
            className="default",
            position=6,
            style=BaseStyle(backgroundColor="#ffffff", color="#000000"),
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1ElementType.FEATURES,
            style=BaseStyle(border="solid", borderRadius="0px"),
            position=7,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1ElementType.CTA,
            position=8,
            enabled=False,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1CTATags.CTA_HEADING_TEXT,
            position=8,
            enabled=False,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1CTATags.CTA_DESCRIPTION_TEXT,
            position=8,
            enabled=False,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1CTATags.CTA_BUTTON,
            style=BaseStyle(borderRadius="8px"),
            position=8,
            enabled=False,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1CTATags.CTA_IMG,
            position=8,
            enabled=False,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1ElementType.BENEFITS,
            style=BaseStyle(border="solid", borderRadius="0px"),
            position=9,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1ElementType.GRID,
            style=BaseStyle(border="solid", borderRadius="0px"),
            position=10,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1ElementType.INNER_CTA,
            style=BaseStyle(border="solid", borderRadius="0px"),
            position=11,
            enabled=False,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1InnerCTATags.INNER_CTA_HEADING_TEXT,
            style=BaseStyle(border="solid", borderRadius="0px"),
            position=11,
            enabled=False,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1InnerCTATags.INNER_CTA_BUTTON,
            style=BaseStyle(border="solid", borderRadius="0px"),
            position=11,
            enabled=False,
        ),
        ElementStyleParam(
            className="default",
            type=Commercial1ElementType.FAQ,
            style=BaseStyle(border="solid", borderRadius="0px"),
            position=12,
        ),
        ElementStyleParam(type=InformationalElementType.RELATED_PAGES, className="default", position=13),
    ]


@dataclass(frozen=True)
class NavigationalPageElementsParams:
    general_style_sample = BaseStyle(
        accentColor="#7792ff", backgroundColor="#ffffff", color="#000000", fontFamily="Roboto"
    )
    elements_param_sample = [
        ElementStyleParam(type=NavigationalElementType.TITLE, position=0),
        ElementStyleParam(type=NavigationalElementType.META_WORDS, position=1),
        ElementStyleParam(type=NavigationalElementType.META_DESCRIPTION, position=2),
        ElementStyleParam(type=NavigationalElementType.META_BACKLINK, position=3, enabled=False),
        ElementStyleParam(type=NavigationalElementType.H1, position=4),
        ElementStyleParam(
            type=NavigationalElementType.PROGRESS_BAR,
            className="default",
            position=5,
            style=BaseStyle(backgroundColor="#ffffff", color="#000000"),
        ),
        ElementStyleParam(type=NavigationalElementType.AUTHOR, position=6),
        ElementStyleParam(type=NavigationalElementType.IMG_FIRST, className="default", position=7),
        ElementStyleParam(type=NavigationalElementType.HEAD_CONTENT, className="default", position=8),
        ElementStyleParam(
            type=NavigationalElementType.TABLE_FIRST,
            className="default",
            style=BaseStyle(backgroundColor="#000000"),
            settings=ElementSettings(tableVariant="horizontal"),
            position=9,
        ),
        ElementStyleParam(type=NavigationalElementType.IMG_SECOND, className="default", position=10),
        ElementStyleParam(
            type=NavigationalElementType.TABLE_SECOND,
            className="default",
            style=BaseStyle(backgroundColor="#000000"),
            settings=ElementSettings(tableVariant="horizontal"),
            position=11,
        ),
        ElementStyleParam(type=NavigationalElementType.IMG_THIRD, className="default", position=12),
        ElementStyleParam(type=NavigationalElementType.NEWS_BUBBLE, className="default", position=13),
        ElementStyleParam(
            type=NavigationalElementType.REFERENCES,
            className="default",
            settings=ElementSettings(reference_follow=False),
            position=14,
        ),
    ]


page_elements_sample_mapper = {
    PageIntent.INFORMATIONAL: InformationalPageElementsParams,
    PageIntent.COMMERCIAL: CommercialPageElementsParams,
    PageIntent.NAVIGATIONAL: NavigationalPageElementsParams,
    PageIntent.TRANSACTIONAL: None,
}
