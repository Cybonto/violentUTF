import uuid
from datetime import datetime

from app.db.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID


class OrchestratorConfiguration(Base):
    """Database model for orchestrator configurations"""

    __tablename__ = "orchestrator_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    orchestrator_type = Column(String(255), nullable=False)
    description = Column(Text)
    parameters = Column(JSON, nullable=False)
    tags = Column(JSON)
    status = Column(String(50), default="configured")
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # PyRIT-specific fields
    pyrit_identifier = Column(JSON)  # Store PyRIT orchestrator identifier
    instance_active = Column(Boolean, default=False)  # Whether instance is currently active


class OrchestratorExecution(Base):
    """Database model for orchestrator executions"""

    __tablename__ = "orchestrator_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    orchestrator_id = Column(UUID(as_uuid=True), nullable=False)
    execution_name = Column(String(255))
    execution_type = Column(String(50))  # 'prompt_list', 'dataset', etc.
    input_data = Column(JSON)  # Store execution input configuration
    status = Column(String(50), default="running")  # 'running', 'completed', 'failed'
    results = Column(JSON)  # Store execution results
    execution_summary = Column(JSON)  # Store summary statistics
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    created_by = Column(String(255))

    # PyRIT-specific fields
    pyrit_memory_session = Column(String(255))  # Track PyRIT memory session
    conversation_ids = Column(JSON)  # List of conversation IDs created
