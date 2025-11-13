from fastapi import APIRouter, status
from starlette.responses import JSONResponse

router = APIRouter()


@router.get(
    "",
    description="Check server.",
    status_code=status.HTTP_200_OK,
)
async def healthcheck() -> JSONResponse:
    return JSONResponse(content="Server works!")
