# /api/v1/api.py

from fastapi import APIRouter
from api.v1.endpoints import (
    memory,targets,datasets, converters, scorers, orchestrators, reports,
    hello
)

api_router = APIRouter()
api_router.include_router(memory.router, tags=["Memory"])
api_router.include_router(targets.router, tags=["Targets"])
#api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
#api_router.include_router(converters.router, prefix="/converters", tags=["Converters"])
#api_router.include_router(scorers.router, prefix="/scorers", tags=["Scorers"])
#api_router.include_router(orchestrators.router, prefix="/orchestrators", tags=["Orchestrators"])
#api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(hello.router, tags=["Hello"])