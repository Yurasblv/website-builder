from pydantic import BaseModel, Field

from .base import BaseStrEnum


class PageType(BaseStrEnum):
    """
    PagePBNHome inheritance types.

    page: default type
    PBN_HOME: Home page type
    PBN_LEGAL: Legal page type
    PBN_CONTACT: Contact page type
    CLUSTER: Cluster page type
    """

    page = "page"
    PBN_EXTRA = "PBN_EXTRA"
    PBN_HOME = "PBN_HOME"
    PBN_LEGAL = "PBN_LEGAL"
    PBN_CONTACT = "PBN_CONTACT"
    CLUSTER = "CLUSTER"

    @property
    def wp_path(self) -> str:
        match self:
            case PageType.PBN_HOME:
                return "home"

            case PageType.PBN_LEGAL:
                return "about"

            case PageType.PBN_CONTACT:
                return "contact"

            case _:
                raise ValueError(f"Invalid page type: {self.value}")

    @classmethod
    def pbn_lead_pages(cls) -> tuple["PageType", ...]:
        return cls.PBN_HOME, cls.PBN_LEGAL, cls.PBN_CONTACT


class PageStatus(BaseStrEnum):
    """
    Statuses for page state.

    DRAFT: Page created without any content
    GENERATED: JSON page generated and ready for build
    BUILT: Page built in HTML format
    """

    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    GENERATING = "GENERATING"
    GENERATION_FAILED = "GENERATION_FAILED"
    BUILT = "BUILT"


class PageIntent(BaseStrEnum):
    TRANSACTIONAL = "TRANSACTIONAL"
    NAVIGATIONAL = "NAVIGATIONAL"
    COMMERCIAL = "COMMERCIAL"
    INFORMATIONAL = "INFORMATIONAL"

    @staticmethod
    def get(intent: str) -> "PageIntent":
        default = PageIntent.INFORMATIONAL
        available = (PageIntent.INFORMATIONAL, PageIntent.COMMERCIAL, PageIntent.NAVIGATIONAL)

        return PageIntent(intent) if intent in available else default


class PageContext(BaseModel):
    summary: str = Field(default="", description="A summary of the content")
    search_intent: PageIntent = Field(default=PageIntent.INFORMATIONAL, description="The search intent of the page")
