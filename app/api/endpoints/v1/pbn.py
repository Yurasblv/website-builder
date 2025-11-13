from fastapi import APIRouter, status
from pydantic import UUID4

from app.api.dependencies import PBNExtraPageGeneratorDep, PBNPagesGeneratorDep, PBNRefreshGeneratorDep
from app.schemas.pbn import PBNGenerationRequest, PBNRefresh
from app.schemas.user_info import UserInfoRead

router = APIRouter(prefix="/pbn", tags=["PBN"])


@router.post(
    "/{money_site_id}/generate",
    description="Generate PBN pages.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate(
    money_site_id: UUID4, user: UserInfoRead, data: PBNGenerationRequest, service: PBNPagesGeneratorDep
) -> None:
    await service.run_dev_generation(user, money_site_id=money_site_id, data=data)


@router.post(
    "/refresh",
    description="Refresh PBN pages.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh(user: UserInfoRead, data: list[PBNRefresh], service: PBNRefreshGeneratorDep) -> None:
    await service.run_dev_generation(user, data=data)


@router.post(
    "/generate/extra-page",
    description="",
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_extra_page(
    user: UserInfoRead,
    pbn_ids: list[UUID4],
    service: PBNExtraPageGeneratorDep,
) -> None:
    await service.run_dev_generation(user, pbn_ids=pbn_ids)
