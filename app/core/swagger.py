from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

swagger_router = APIRouter()
security = HTTPBasic()


@swagger_router.get(
    "/docs",
    include_in_schema=False,
    response_class=HTMLResponse,
)
async def get_docs() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=f"/{settings.PROJECT_NAME}/openapi.json", title="NDA AI Builder API Swagger"
    )


@swagger_router.get("/redoc", include_in_schema=False, response_class=Response)
async def get_redoc() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=f"/{settings.PROJECT_NAME}/openapi.json", title="NDA AI Builder Redoc", with_google_fonts=True
    )


@swagger_router.get(
    f"/{settings.PROJECT_NAME}/openapi.json",
    include_in_schema=False,
    response_class=JSONResponse,
)
async def get_openapi_json(creds: HTTPBasicCredentials = Depends(security)) -> JSONResponse:
    from app.api import api_router

    if creds.username != settings.SWAGGER_USERNAME or creds.password != settings.SWAGGER_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")

    openapi_schema = get_openapi(version="1.0.0", title="NDA AI Builder OpenAPI", routes=api_router.routes)
    return JSONResponse(openapi_schema)
