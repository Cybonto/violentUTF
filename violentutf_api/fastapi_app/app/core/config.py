# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Application configuration using Pydantic Settings."""

import os
from pathlib import Path
from typing import Any, List, Optional, Union

from pydantic import AnyHttpUrl, Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project info
    PROJECT_NAME: str = "ViolentUTF API"
    DESCRIPTION: str = "Programmatic interface for ViolentUTF LLM red-teaming platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SERVICE_NAME: str = Field(default="ViolentUTF API", env="SERVICE_NAME")
    SERVICE_VERSION: str = Field(default="1.0.0", env="SERVICE_VERSION")

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # Security
    SECRET_KEY: str = Field(default="", env="SECRET_KEY")
    JWT_SECRET_KEY: str = Field(default="", env="JWT_SECRET_KEY")  # For Streamlit compatibility
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 30 minutes
    API_KEY_EXPIRE_DAYS: int = Field(default=365, env="API_KEY_EXPIRE_DAYS")
    ALGORITHM: str = "HS256"

    @validator("JWT_SECRET_KEY", always=True)
    def set_jwt_secret_key(cls, v, values) -> Any:
        """Use SECRET_KEY if JWT_SECRET_KEY is not set."""
        return v or values.get("SECRET_KEY", "")

    # CORS
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = Field(
        default=["http://localhost", "http://localhost:3000", "http://localhost:8501"], env="BACKEND_CORS_ORIGINS"
    )

    # Database
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")

    # External services
    KEYCLOAK_URL: str = Field(default="http://localhost:8080", env="KEYCLOAK_URL")
    KEYCLOAK_REALM: str = Field(default="ViolentUTF", env="KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID: str = Field(default="violentutf-api", env="KEYCLOAK_CLIENT_ID")
    KEYCLOAK_CLIENT_SECRET: str = Field(default="", env="KEYCLOAK_CLIENT_SECRET")

    APISIX_BASE_URL: str = Field(default="http://localhost:9080", env="APISIX_BASE_URL")
    APISIX_ADMIN_URL: str = Field(default="http://localhost:9180", env="APISIX_ADMIN_URL")
    APISIX_ADMIN_KEY: str = Field(default="", env="APISIX_ADMIN_KEY")
    VIOLENTUTF_API_KEY: str = Field(default="", env="VIOLENTUTF_API_KEY")

    # Docker Network Configuration (added for container-to-container communication)
    VIOLENTUTF_API_URL: Optional[str] = Field(default=None, env="VIOLENTUTF_API_URL")
    APISIX_CONTAINER_NAME: Optional[str] = Field(default="apisix-apisix-1", env="APISIX_CONTAINER_NAME")
    KEYCLOAK_CONTAINER_NAME: Optional[str] = Field(default="keycloak-keycloak-1", env="KEYCLOAK_CONTAINER_NAME")

    # User Context Configuration
    DEFAULT_USERNAME: str = Field(default="violentutf.web", env="DEFAULT_USERNAME")

    # Generator Type Configuration
    GENERATOR_TYPE_MAPPING: Optional[str] = Field(default=None, env="GENERATOR_TYPE_MAPPING")

    # APISIX Gateway Authentication
    APISIX_GATEWAY_SECRET: str = Field(default="", env="APISIX_GATEWAY_SECRET")

    # External URL for OAuth callbacks
    EXTERNAL_URL: Optional[str] = Field(default=None, env="EXTERNAL_URL")

    # File paths
    APP_DATA_DIR: Path = Field(default=Path("./app_data"), env="APP_DATA_DIR")
    CONFIG_DIR: Path = Field(default=Path("./config"), env="CONFIG_DIR")

    # PyRIT Configuration
    PYRIT_MEMORY_DB_PATH: str = Field(default="/app/app_data/violentutf", env="PYRIT_MEMORY_DB_PATH")
    PYRIT_DB_SALT: str = Field(default="", env="PYRIT_DB_SALT")

    # AI Provider Configuration (from ai-tokens.env)
    # These enable/disable providers in the UI
    OPENAI_ENABLED: bool = Field(default=False, env="OPENAI_ENABLED")
    ANTHROPIC_ENABLED: bool = Field(default=False, env="ANTHROPIC_ENABLED")
    OLLAMA_ENABLED: bool = Field(default=False, env="OLLAMA_ENABLED")
    OPEN_WEBUI_ENABLED: bool = Field(default=False, env="OPEN_WEBUI_ENABLED")
    OPENAPI_ENABLED: bool = Field(default=False, env="OPENAPI_ENABLED")

    # OpenAPI Provider Configurations (for dynamic model discovery)
    # Support up to 10 OpenAPI providers (OPENAPI_1_* through OPENAPI_10_*)
    OPENAPI_1_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_1_ENABLED")
    OPENAPI_1_ID: Optional[str] = Field(default=None, env="OPENAPI_1_ID")
    OPENAPI_1_NAME: Optional[str] = Field(default=None, env="OPENAPI_1_NAME")
    OPENAPI_1_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_1_BASE_URL")
    OPENAPI_1_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_1_AUTH_TOKEN")
    OPENAPI_1_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_1_AUTH_TYPE")
    OPENAPI_1_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_1_SPEC_PATH")

    OPENAPI_2_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_2_ENABLED")
    OPENAPI_2_ID: Optional[str] = Field(default=None, env="OPENAPI_2_ID")
    OPENAPI_2_NAME: Optional[str] = Field(default=None, env="OPENAPI_2_NAME")
    OPENAPI_2_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_2_BASE_URL")
    OPENAPI_2_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_2_AUTH_TOKEN")
    OPENAPI_2_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_2_AUTH_TYPE")
    OPENAPI_2_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_2_SPEC_PATH")

    OPENAPI_3_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_3_ENABLED")
    OPENAPI_3_ID: Optional[str] = Field(default=None, env="OPENAPI_3_ID")
    OPENAPI_3_NAME: Optional[str] = Field(default=None, env="OPENAPI_3_NAME")
    OPENAPI_3_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_3_BASE_URL")
    OPENAPI_3_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_3_AUTH_TOKEN")
    OPENAPI_3_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_3_AUTH_TYPE")
    OPENAPI_3_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_3_SPEC_PATH")

    OPENAPI_4_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_4_ENABLED")
    OPENAPI_4_ID: Optional[str] = Field(default=None, env="OPENAPI_4_ID")
    OPENAPI_4_NAME: Optional[str] = Field(default=None, env="OPENAPI_4_NAME")
    OPENAPI_4_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_4_BASE_URL")
    OPENAPI_4_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_4_AUTH_TOKEN")
    OPENAPI_4_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_4_AUTH_TYPE")
    OPENAPI_4_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_4_SPEC_PATH")

    OPENAPI_5_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_5_ENABLED")
    OPENAPI_5_ID: Optional[str] = Field(default=None, env="OPENAPI_5_ID")
    OPENAPI_5_NAME: Optional[str] = Field(default=None, env="OPENAPI_5_NAME")
    OPENAPI_5_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_5_BASE_URL")
    OPENAPI_5_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_5_AUTH_TOKEN")
    OPENAPI_5_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_5_AUTH_TYPE")
    OPENAPI_5_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_5_SPEC_PATH")

    OPENAPI_6_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_6_ENABLED")
    OPENAPI_6_ID: Optional[str] = Field(default=None, env="OPENAPI_6_ID")
    OPENAPI_6_NAME: Optional[str] = Field(default=None, env="OPENAPI_6_NAME")
    OPENAPI_6_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_6_BASE_URL")
    OPENAPI_6_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_6_AUTH_TOKEN")
    OPENAPI_6_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_6_AUTH_TYPE")
    OPENAPI_6_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_6_SPEC_PATH")

    OPENAPI_7_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_7_ENABLED")
    OPENAPI_7_ID: Optional[str] = Field(default=None, env="OPENAPI_7_ID")
    OPENAPI_7_NAME: Optional[str] = Field(default=None, env="OPENAPI_7_NAME")
    OPENAPI_7_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_7_BASE_URL")
    OPENAPI_7_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_7_AUTH_TOKEN")
    OPENAPI_7_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_7_AUTH_TYPE")
    OPENAPI_7_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_7_SPEC_PATH")

    OPENAPI_8_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_8_ENABLED")
    OPENAPI_8_ID: Optional[str] = Field(default=None, env="OPENAPI_8_ID")
    OPENAPI_8_NAME: Optional[str] = Field(default=None, env="OPENAPI_8_NAME")
    OPENAPI_8_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_8_BASE_URL")
    OPENAPI_8_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_8_AUTH_TOKEN")
    OPENAPI_8_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_8_AUTH_TYPE")
    OPENAPI_8_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_8_SPEC_PATH")

    OPENAPI_9_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_9_ENABLED")
    OPENAPI_9_ID: Optional[str] = Field(default=None, env="OPENAPI_9_ID")
    OPENAPI_9_NAME: Optional[str] = Field(default=None, env="OPENAPI_9_NAME")
    OPENAPI_9_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_9_BASE_URL")
    OPENAPI_9_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_9_AUTH_TOKEN")
    OPENAPI_9_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_9_AUTH_TYPE")
    OPENAPI_9_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_9_SPEC_PATH")

    OPENAPI_10_ENABLED: Optional[bool] = Field(default=None, env="OPENAPI_10_ENABLED")
    OPENAPI_10_ID: Optional[str] = Field(default=None, env="OPENAPI_10_ID")
    OPENAPI_10_NAME: Optional[str] = Field(default=None, env="OPENAPI_10_NAME")
    OPENAPI_10_BASE_URL: Optional[str] = Field(default=None, env="OPENAPI_10_BASE_URL")
    OPENAPI_10_AUTH_TOKEN: Optional[str] = Field(default=None, env="OPENAPI_10_AUTH_TOKEN")
    OPENAPI_10_AUTH_TYPE: Optional[str] = Field(default=None, env="OPENAPI_10_AUTH_TYPE")
    OPENAPI_10_SPEC_PATH: Optional[str] = Field(default=None, env="OPENAPI_10_SPEC_PATH")

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v: str) -> str:
        if not v:
            # Generate a default secret key for development
            import secrets

            return secrets.token_urlsafe(32)
        return v

    @validator("APISIX_GATEWAY_SECRET", pre=True)
    def validate_apisix_gateway_secret(cls, v: str) -> str:
        if not v:
            # Generate a default gateway secret for development
            import secrets

            return secrets.token_urlsafe(32)
        return v

    @validator("APP_DATA_DIR", "CONFIG_DIR", pre=True)
    def validate_paths(cls, v: Union[str, Path]) -> Path:
        path = Path(v) if isinstance(v, str) else v
        path.mkdir(parents=True, exist_ok=True)
        return path

    model_config = {"env_file": ".env", "case_sensitive": True}


# Create global settings instance
settings = Settings()
