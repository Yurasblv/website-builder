from fastapi import APIRouter, Query, status

from app.schemas import ListElementOutput
from app.services.domain.manager import DomainAIService

router = APIRouter(prefix="/domains", tags=["Domains"])


@router.get(
    "/ai",
    description="Generate AI domains",
    response_model=ListElementOutput,
    status_code=status.HTTP_200_OK,
)
async def ban_words(
    keyword: str = Query(
        ...,
        title="Keyword",
        description="Keyword to generate domains.",
    ),
    category: str = Query(
        ...,
        title="Category",
        description="Category of the domain.",
    ),
) -> ListElementOutput:
    return await DomainAIService.generate_ai_domains(keyword=keyword, category=category)
