from fastapi import APIRouter, status
from pydantic import UUID4

from app.utils.qa import check_ban_words

router = APIRouter()


@router.get(
    "/{page_id}/ban-words",
    description="Check ban words in page.",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
)
async def ban_words(page_id: UUID4) -> list[str]:
    return await check_ban_words(page_id)
