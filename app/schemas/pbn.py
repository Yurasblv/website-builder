from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from asyncpg.pgproto.pgproto import timedelta
from fastapi import Query
from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from app.core.exc.pbn import MoneysiteRequestException
from app.enums import (
    BacklinkPublishPeriodEnum,
    Country,
    GenerationStatus,
    Language,
    PageType,
    PBNGenerationStatus,
    PBNPlanType,
    PBNTierType,
)
from app.models import Author
from app.schemas.backlink import BacklinkCreate
from app.schemas.cluster.base import ClusterSettingsRead
from app.schemas.domains import DomainResponse
from app.schemas.page.cluster_page import ClusterPageCreate


class PBNFilters(BaseModel):
    status: PBNGenerationStatus | None = Field(None, description="Status of the PBN generation process.")
    domain__category_id__in: list[UUID4] | None = Field(
        None, description="Categories of the domain, defining its niche or industry."
    )
    tier: PBNTierType | None = Field(None, description="Tier level of the PBN, indicating its authority or importance.")
    language: Language | None = Field(None, description="Primary language of the PBN domain.")

    @classmethod
    def as_query(
        cls,
        status: PBNGenerationStatus | None = Query(None),
        domain__category_id__in: list[UUID4] | None = Query(None),
        tier: PBNTierType | None = Query(None),
        language: Language | None = Query(None),
    ) -> "PBNFilters":
        return cls(status=status, domain__category_id__in=domain__category_id__in, tier=tier, language=language)


class PBNResponse(BaseModel):
    id: UUID4
    name: str
    status: PBNGenerationStatus
    category_id: UUID4
    language: Language
    tier: PBNTierType
    money_site_url: str
    expired_at: datetime | None

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PBNPlanRead(BaseModel):
    id: UUID4
    type: PBNPlanType
    option: int
    structure: dict
    websites_amount: int
    pages_amount: int
    price: Decimal
    created_at: datetime


class PBNPlanStructureRead(BaseModel):
    id: UUID4 = Field(default_factory=uuid4)
    tier: PBNTierType
    backlink: bool = Field(default=False)
    pages: int = Field(default=0)
    parent_id: UUID4 | None = None
    children: list["PBNPlanStructureRead"] = Field(default_factory=list, examples=[[]])

    @classmethod
    def __construct_tree(
        cls, structure: dict, root_tier: PBNTierType, tiers: list[PBNTierType], parent_id: UUID4 = None
    ) -> list["PBNPlanStructureRead"]:
        """
        Construct the tree structure recursively from the provided structure dictionary.

        Args:
            structure: A dictionary where each key is a tier name and each value is a list of page counts.
            root_tier: The current tier to process (e.g., T1, T2, etc.).
            tiers: A list of tier names that defines the hierarchy.
            parent_id: The parent node ID to associate with the current node.

        Returns:
            A list of PBNPlanStructureRead instances representing the constructed tree.
        """

        children = []

        root_tier_data = structure.get(root_tier, {})
        count = root_tier_data.get("count") or 0
        pages = root_tier_data.get("pages") or 0

        for _ in range(count):
            node = cls(tier=root_tier, parent_id=parent_id if root_tier != PBNTierType.T1 else None, pages=pages)

            next_tier_index = tiers.index(root_tier) + 1

            if next_tier_index < len(tiers):
                next_tier = tiers[next_tier_index]
                node.children = cls.__construct_tree(structure, next_tier, tiers, node.id)

            children.append(node)

        return children

    @classmethod
    def __construct_list(cls, node: "PBNPlanStructureRead", result: list) -> None:
        result.append(node)
        for child in node.children:
            cls.__construct_list(child, result)

    @classmethod
    def to_tree(cls, structure: dict[str, list], tiers: list[PBNTierType]) -> Optional["PBNPlanStructureRead"]:
        """
        Convert the given structure into a hierarchical tree.

        Args:
            structure: A dictionary representing the structure to be converted into a tree.
            tiers: A list of tiers to define the hierarchy.

        Returns:
            The root of the tree, or None if the structure is empty.
        """

        root = PBNPlanStructureRead(tier=tiers[0])
        root.children = cls.__construct_tree(structure, root_tier=tiers[0], tiers=tiers, parent_id=root.id)

        if root.children:
            return root.children[0]

    @classmethod
    def to_list(cls, root: "PBNPlanStructureRead", amount: int) -> list["PBNPlanStructureRead"]:
        """
        Convert the given structure into a flat list.

        Args:
            root: The root of the tree to be converted into a list.
            amount: The expected number of items in the list.

        Raises:
            MoneysiteRequestException: If the number of items in the list does not match the expected amount.

        Returns:
            A list of PBNPlanStructureRead instances representing the flat structure.
        """

        result = [root]
        for child in root.children:
            cls.__construct_list(child, result)

        if len(result) == amount:
            return result

        raise MoneysiteRequestException("The number of websites in the structure does not match the plan.")


class PBNPlanCreate(PBNPlanRead):
    id: UUID4 = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MoneySiteRead(BaseModel):
    id: UUID4
    url: str
    keyword: str

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class MoneySiteCreate(MoneySiteRead):
    id: UUID4
    user_id: UUID4
    plan_id: UUID4

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_to_uuid(cls, v: UUID4 | None) -> UUID4:
        return v or uuid4()


class PBNGenerationRequest(BaseModel):
    keyword: str
    domain_uuid_list: list[UUID4]
    backlink_publish_period_option: BacklinkPublishPeriodEnum | None = BacklinkPublishPeriodEnum.IMMEDIATE

    language: Language
    country: Country
    money_site_url: HttpUrl
    plan_id: UUID4
    pbn_structure: PBNPlanStructureRead

    @property
    def money_site_domain(self) -> str:
        """Extract the domain from the money_site_url."""

        parsed_url = urlparse(str(self.money_site_url))
        return parsed_url.netloc.replace("www.", "")


class PBNBacklinkInfo(BaseModel):
    page_type: PageType
    publish_at: datetime


class PBNBatchRequest(BaseModel):
    pbn_ids: list[UUID4] = Field(default_factory=list, examples=[["115a0a9e-0f87-43b9-a186-97105d79e626"]])


class PBNClusterCreate(BaseModel):
    id: UUID4
    pbn_id: UUID4 | None = None
    keyword: str
    language: Language
    target_country: Country
    target_audience: str | None = None
    link: str | None = None
    topics_number: int
    status: GenerationStatus
    created_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
    user_id: UUID4
    author: Author
    industry_id: UUID4
    pages: list[ClusterPageCreate] = []
    settings: list[ClusterSettingsRead] = []
    backlink: BacklinkCreate | None

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PBNGenerate(BaseModel):
    id: UUID4
    user_id: UUID4
    user_email: EmailStr | str
    keyword: str
    money_site_url: str
    tier: PBNTierType
    pages_number: int
    domain: DomainResponse
    category: str
    status: PBNGenerationStatus = PBNGenerationStatus.DRAFT
    template: str
    target_country: Country
    language: Language
    server_id: UUID4 | None = None
    money_site_id: UUID4
    service_account_id: UUID4
    expired_at: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(days=365))
    parent_id: UUID4 | None
    backlink_page: PageType | None = None
    backlink_publish_period_option: BacklinkPublishPeriodEnum | None = None

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @property
    def money_site_domain(self) -> str:
        """Extract the domain from the money_site_url."""

        parsed_url = urlparse(str(self.money_site_url))
        return parsed_url.netloc.replace("www.", "")


class PBNClusterRead(BaseModel):
    id: UUID4
    link: str
    keyword: str
    topics_number: int


class PBNRefresh(BaseModel):
    id: UUID4
    user_id: UUID4
    user_email: str
    pages_number: int
    status: PBNGenerationStatus
    wp_token: str
    wp_port: str
    host: str
    clusters: list[PBNClusterRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @property
    def upload_pbn_url(self) -> str:
        return f"http://{self.host}:{self.wp_port}/"


class PBNDeploy(PBNRefresh):
    money_site_id: UUID4
    money_site_url: str

    @property
    def not_built(self) -> bool:
        return any([self.status == PBNGenerationStatus.GENERATED, self.status == PBNGenerationStatus.BUILD_FAILED])

    @property
    def not_deployed(self) -> bool:
        return self.status == PBNGenerationStatus.DEPLOY_FAILED


class PBNCreate(BaseModel):
    id: UUID4

    template: str
    tier: PBNTierType
    status: PBNGenerationStatus
    target_country: Country
    language: Language
    expired_at: datetime | None = None
    pages_number: int

    user_id: UUID4
    server_id: UUID4 | None = None
    money_site_id: UUID4
    service_account_id: UUID4
    parent_id: UUID4 | None

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PBNRead(BaseModel):
    id: UUID4
    domain: DomainResponse | None
    pages_number: int
    status: PBNGenerationStatus
    tier: PBNTierType
    language: Language
    money_site: MoneySiteRead
    updated_at: datetime
    expired_at: datetime | None
    launch_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PaginatedPBNResponse(BaseModel):
    count: int = Field(0, description="Number of total items")
    total_pages: int = Field(0, description="Number of total pages")
    items: list[PBNRead] = Field(default_factory=list, description="List of items returned in a paginated response")

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class PBNRenewRequest(BaseModel):
    keyword: str = Field(..., description="Money site's keyword")
    name: str | None = Field(default=None, description="User's first name using in template")
    email: str = Field(..., description="User's email")


class PBNLeadPageImageMetadata(BaseModel):
    prompt: str = Field(..., description="Query to search an image in the pictures stock.")
    image_alt_tag: str = Field(..., description="Image alt tag.")


class PBNDomainRenewRequest(BaseModel):
    keyword: str = Field(..., description="Money site's keyword")
    name: str | None = Field(default=None, description="User's first name using in template")
    email: str = Field(..., description="User's email")


class Tag(BaseModel):
    tag_placeholder: str = Field(
        ..., description="Placeholder for a web element consisting of HTML tag, name and uuid."
    )
    new_content: str = Field(..., description="New content for a given web element.")


class UpdatedTags(BaseModel):
    updated_tags: list[Tag] = Field(..., description="List of updated tags")


class PBNQueueResponse(BaseModel):
    money_site_id: UUID4
    money_site_url: str
    queue: int


class PBNBacklinkResponse(BaseModel):
    sentence: str = Field(..., description="Sentence containing a backlink")
    anchor: str = Field(..., description="Phrase to which a backlink will be attached")
