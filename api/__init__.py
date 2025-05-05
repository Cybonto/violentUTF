# /api/__init__.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.api import api_router
from core.config import settings

app = FastAPI(
    title="ViolentUTF API",
    description="ViolentUTF - Red Teaming and Testing for Generative AI",
    version="1.0.0"
)

# CORS Configuration (Optional, but recommended)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"], # e.g., Streamlit frontend, etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your API router
app.include_router(api_router, prefix="/api/v1")