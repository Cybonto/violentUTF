from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OrchestratorTypeInfo(BaseModel):
    """Schema for orchestrator type information"""

    name: str
    module: str
    category: str
    description: str
    use_cases: List[str]
    parameters: List[Dict[str, Any]]


class OrchestratorConfigCreate(BaseModel):
    """Schema for creating orchestrator configuration"""

    name: str = Field(..., description="Unique name for the orchestrator")
    orchestrator_type: str = Field(..., description="Type of orchestrator (e.g., PromptSendingOrchestrator)")
    description: Optional[str] = Field(None, description="Description of the orchestrator")
    parameters: Dict[str, Any] = Field(..., description="Orchestrator parameters")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")


class OrchestratorConfigResponse(BaseModel):
    """Schema for orchestrator configuration response"""

    orchestrator_id: UUID
    name: str
    orchestrator_type: str
    status: str
    created_at: datetime
    parameters_validated: bool
    pyrit_identifier: Optional[Dict[str, str]] = None


# DEPRECATED: These schemas are replaced by RESTful equivalents
# OrchestratorExecuteRequest -> ExecutionCreate
# OrchestratorExecuteResponse -> ExecutionResponse
# Use the RESTful schemas below for new implementations


class OrchestratorExecuteRequest(BaseModel):
    """DEPRECATED: Use ExecutionCreate for RESTful API"""

    execution_type: str = Field(..., description="Type of execution (prompt_list, dataset)")
    execution_name: Optional[str] = Field(None, description="Name for this execution")
    input_data: Dict[str, Any] = Field(..., description="Input data for execution")


class OrchestratorExecuteResponse(BaseModel):
    """DEPRECATED: Use ExecutionResponse for RESTful API"""

    execution_id: UUID
    status: str
    orchestrator_id: UUID
    orchestrator_type: str
    execution_name: Optional[str]
    started_at: datetime
    expected_operations: int
    progress: Dict[str, Any]
    pyrit_memory_id: Optional[str] = None


# New RESTful schemas for Phase 1 implementation
class ExecutionCreate(BaseModel):
    """Schema for creating a new execution (RESTful)"""

    execution_type: str = Field(..., description="Type of execution (prompt_list, dataset)")
    execution_name: Optional[str] = Field(None, description="Name for this execution")
    input_data: Dict[str, Any] = Field(..., description="Input data for execution")


class ExecutionResponse(BaseModel):
    """Schema for execution resource response (RESTful)"""

    id: UUID
    orchestrator_id: UUID
    execution_type: str
    execution_name: Optional[str]
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    input_data: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None
    execution_summary: Optional[Dict[str, Any]] = None
    created_by: str
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


class ExecutionListResponse(BaseModel):
    """Schema for listing executions (RESTful)"""

    executions: List[ExecutionResponse]
    total: int
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


class OrchestratorResultsResponse(BaseModel):
    """Schema for orchestrator execution results"""

    execution_id: UUID
    status: str
    orchestrator_name: str
    orchestrator_type: str
    execution_summary: Dict[str, Any]
    prompt_request_responses: List[Dict[str, Any]]
    scores: List[Dict[str, Any]]
    memory_export: Dict[str, Any]


class OrchestratorMemoryResponse(BaseModel):
    """Schema for orchestrator memory response"""

    orchestrator_id: UUID
    memory_pieces: List[Dict[str, Any]]
    total_pieces: int
    conversations: int


class OrchestratorScoresResponse(BaseModel):
    """Schema for orchestrator scores response"""

    orchestrator_id: UUID
    scores: List[Dict[str, Any]]
    total_scores: int
