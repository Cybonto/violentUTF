# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Main API router that includes all sub-routers."""

from fastapi import APIRouter

from app.api.endpoints import (
    apisix_admin,
    auth,
    config,
    converters,
    database,
    datasets,
    debug_jwt,
    echo,
    files,
    generators,
    health,
    jwt_keys,
    orchestrators,
    redteam,
    scorers,
    sessions,
    validation,
)
from app.api.v1 import assets, risk

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(debug_jwt.router, tags=["debug"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(jwt_keys.router, prefix="/keys", tags=["jwt-keys"])
api_router.include_router(echo.router, prefix="/echo", tags=["echo"])

# New endpoints for 0_Welcome.py support
api_router.include_router(database.router, prefix="/database", tags=["database"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(config.router, prefix="/config", tags=["configuration"])
api_router.include_router(files.router, prefix="/files", tags=["files"])

# Generator management endpoints for 1_Configure_Generators.py
api_router.include_router(generators.router, prefix="/generators", tags=["generators"])

# Dataset management endpoints for 2_Configure_Datasets.py
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])

# Converter management endpoints for 3_Configure_Converters.py
api_router.include_router(converters.router, prefix="/converters", tags=["converters"])

# Scorer management endpoints for 4_Configure_Scorers.py
api_router.include_router(scorers.router, prefix="/scorers", tags=["scorers"])

# Red-teaming endpoints for PyRIT and Garak integration
api_router.include_router(redteam.router, prefix="/redteam", tags=["red-teaming"])

# Orchestrator management endpoints for PyRIT orchestrator API
api_router.include_router(orchestrators.router, prefix="/orchestrators", tags=["orchestrators"])

# APISIX admin endpoints for IronUTF plugin management
api_router.include_router(apisix_admin.router)

# Dataset validation endpoints (Issue #120)
api_router.include_router(validation.router, prefix="/validation", tags=["validation"])

# Asset management endpoints (Issue #280)
api_router.include_router(assets.router, prefix="/assets", tags=["asset-management"])

# Risk assessment endpoints (Issue #282)
api_router.include_router(risk.router, prefix="/risk", tags=["risk-assessment"])
