# /models/memory.py

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from typing import List

class BaseMemoryConfiguration(BaseModel):
    memory_type: Literal["InMemory", "DuckDB", "AzureSQL"] = Field(
        ...,
        description="The type of memory backend to use."
    )

    @field_validator('memory_type')
    def validate_memory_type(cls, v):
        if v not in ["InMemory", "DuckDB", "AzureSQL"]:
            raise ValueError(f"Unsupported memory_type: {v}")
        return v

class InMemoryConfiguration(BaseMemoryConfiguration):
    memory_type: Literal["InMemory"] = "InMemory"

class DuckDBConfiguration(BaseMemoryConfiguration):
    memory_type: Literal["DuckDB"] = "DuckDB"
    db_path: str = Field(
        default="app_data/violentutf/duckdb/pyrit.db",
        description="File path to the DuckDB database file."
    )

class AzureSQLConfiguration(BaseMemoryConfiguration):
    memory_type: Literal["AzureSQL"] = "AzureSQL"
    connection_string: str = Field(
        ...,
        description="SQLAlchemy connection string for the Azure SQL Database."
    )
    results_container_url: str = Field(
        ...,
        description="URL of the Azure Blob Storage container used for storing associated files."
    )
    results_sas_token: Optional[str] = Field(
        None,
        description="Shared Access Signature token for accessing the Azure Blob Storage container."
    )

# Union type for Memory Configuration Request
MemoryConfigurationRequest = InMemoryConfiguration | DuckDBConfiguration | AzureSQLConfiguration

class MemoryConfigurationResponse(BaseModel):
    success: bool = Field(
        ...,
        description="Indicates whether the memory configuration was successful."
    )
    message: Optional[str] = Field(
        None,
        description="Additional information or error message."
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional details about the configuration or errors."
    )

class MessageCreateRequest(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="The role of the message sender."
    )
    content: str = Field(
        ..., description="Content of the message."
    )
    labels: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Labels associated with the message."
    )
    prompt_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata for the message."
    )

class MessageResponse(BaseModel):
    id: str = Field(
        ..., description="Unique identifier of the message."
    )
    conversation_id: str = Field(
        ..., description="Identifier of the conversation."
    )
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="Role of the message sender."
    )
    content: str = Field(
        ..., description="Content of the message."
    )
    timestamp: datetime = Field(
        ..., description="Timestamp of the message."
    )
    labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Labels associated with the message."
    )
    prompt_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the message."
    )

class ConversationHistoryResponse(BaseModel):
    messages: List[MessageResponse] = Field(
        ..., description="List of messages in the conversation."
    )

