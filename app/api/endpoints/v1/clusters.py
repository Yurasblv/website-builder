from fastapi import APIRouter, status
from pydantic import UUID4

from app.api.dependencies import UnitOfWorkDep
from app.enums import Language
from app.schemas.cluster.base import ClusterCreateData
from app.services import ClusterService
from app.services.generation.cluster.structure import ClusterStructureGenerator

router = APIRouter(prefix="/clusters", tags=["Clusters"])


@router.get(
    "/author",
    response_model=UUID4,
    description="Define author for article or batch of articles.",
    status_code=status.HTTP_200_OK,
)
async def get_cluster_author(
    user_id: UUID4,
    industry_id: UUID4,
    keyword: str,
    language: Language,
) -> UUID4:
    return await ClusterStructureGenerator.define_author(
        user_id=user_id,
        industry_id=industry_id,
        keyword=keyword,
        language=language,
    )


@router.get(
    "/industry",
    response_model=UUID4,
    description="Define industry for article or batch of articles.",
    status_code=status.HTTP_200_OK,
)
async def get_cluster_industry(keyword: str, language: Language) -> UUID4:
    return await ClusterStructureGenerator.define_industry(
        keyword=keyword,
        language=language,
    )


@router.get(
    "/validate-keyword",
    response_model=bool,
    description="Validate keyword.",
    status_code=status.HTTP_200_OK,
)
async def validate_cluster_keyword(keyword: str, language: Language) -> bool:
    return await ClusterStructureGenerator.validate_keyword(
        keyword=keyword,
        language=language,
    )


@router.post(
    "/{cluster_id}/refresh",
    description="Refresh cluster.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh(unit_of_work: UnitOfWorkDep, cluster_id: UUID4) -> None:
    await ClusterService.upgrade_current_version(unit_of_work, cluster_id=cluster_id)


@router.post(
    "/{cluster_id}/build",
    description="Build cluster.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def build(unit_of_work: UnitOfWorkDep, cluster_id: UUID4) -> None:
    await ClusterService.building(unit_of_work, cluster_id=cluster_id)


@router.post(
    "/{cluster_id}/generate",
    description="Generate cluster.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate(unit_of_work: UnitOfWorkDep, cluster_id: UUID4) -> None:
    await ClusterService.generate(unit_of_work, cluster_id=cluster_id)


@router.post(
    "/{cluster_id}/create",
    description="Create cluster.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def create(cluster_id: UUID4, data: ClusterCreateData) -> None:
    await ClusterService.create(cluster_id=cluster_id, data=data)
