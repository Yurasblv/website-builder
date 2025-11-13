from fastapi import APIRouter

from .clusters import router as clusters
from .domains import router as domains
from .pbn import router as pbn
from .qa import router as qa

api_router = APIRouter(prefix="/v1")

api_router.include_router(clusters)
api_router.include_router(domains)
api_router.include_router(qa, prefix="/qa", tags=["QA"])
api_router.include_router(pbn)
