from fastapi import APIRouter

from .health_check import router as health_check
from .v1 import api_router as v1

api_router = APIRouter(prefix="/api")

api_router.include_router(health_check, prefix="/health-check", tags=["Health check"])
api_router.include_router(v1)
