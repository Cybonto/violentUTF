"""
Pydantic schemas for scorer management API
Implements API backend for 4_Configure_Scorers.py page
SECURITY: Enhanced with comprehensive input validation to prevent injection attacks
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Literal
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum

from app.core.validation import (
    sanitize_string, validate_generator_parameters, SecurityLimits,
    ValidationPatterns, create_validation_error
)

# Enums for better type safety
class ScorerCategoryType(str, Enum):
    PATTERN_MATCHING = "Pattern Matching Scorers"
    SELF_ASK_FAMILY = "Self-Ask Scorer Family"
    SECURITY_DETECTION = "Security and Attack Detection"
    HUMAN_EVALUATION = "Human Evaluation"
    UTILITY_META = "Utility and Meta-Scoring"
    CLOUD_PROFESSIONAL = "Cloud-Based Professional Scorers"

class ParameterType(str, Enum):
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    LIST = "list"
    DICT = "dict"
    COMPLEX = "complex"

# Parameter definition models
class ScorerParameter(BaseModel):
    """Definition of a scorer parameter"""
    name: str = Field(..., description="Parameter name")
    description: str = Field(..., description="Human-readable parameter description")
    primary_type: str = Field(..., description="Primary Python type")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value")
    literal_choices: Optional[List[str]] = Field(None, description="Available literal choices")
    skip_in_ui: bool = Field(default=False, description="Skip parameter in UI")

# Scorer category information
class ScorerCategoryInfo(BaseModel):
    """Information about a scorer category"""
    description: str = Field(..., description="Category description")
    strengths: List[str] = Field(..., description="Category strengths")
    limitations: List[str] = Field(..., description="Category limitations")
    best_scenarios: List[str] = Field(..., description="Best use case scenarios")
    scorers: List[str] = Field(..., description="Available scorers in category")

# Test case models
class CategoryTestCase(BaseModel):
    """Test case for a scorer category"""
    category: str = Field(..., description="Scorer category")
    test_inputs: List[str] = Field(..., description="Sample test inputs")

# Scorer operation models
class ScorerCreateRequest(BaseModel):
    """Request model for creating a scorer"""
    name: str = Field(..., min_length=3, max_length=SecurityLimits.MAX_NAME_LENGTH, description="Unique scorer configuration name")
    scorer_type: str = Field(..., min_length=3, max_length=100, description="Scorer class name")
    parameters: Dict[str, Any] = Field(default={}, description="Scorer parameters")
    generator_id: Optional[str] = Field(None, max_length=100, description="Generator ID for chat_target parameter")
    
    @validator('name')
    def validate_name_field(cls, v):
        """Validate scorer name"""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Name must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    @validator('scorer_type')
    def validate_scorer_type_field(cls, v):
        """Validate scorer type"""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Scorer type must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    @validator('parameters')
    def validate_parameters_field(cls, v):
        """Validate scorer parameters"""
        return validate_generator_parameters(v)
    
    @validator('generator_id')
    def validate_generator_id_field(cls, v):
        """Validate generator ID"""
        if v is not None:
            v = sanitize_string(v)
            if len(v) > 100:
                raise ValueError("Generator ID too long")
        return v

class ScorerCreateResponse(BaseModel):
    """Response model for scorer creation"""
    success: bool = Field(..., description="Whether creation was successful")
    scorer: Dict[str, Any] = Field(..., description="Created scorer information")
    message: str = Field(..., description="Success or error message")


class ScorerCloneRequest(BaseModel):
    """Request model for cloning a scorer"""
    new_name: str = Field(..., min_length=3, max_length=SecurityLimits.MAX_NAME_LENGTH, description="Name for the cloned scorer")
    clone_parameters: bool = Field(default=True, description="Whether to clone parameters")
    
    @validator('new_name')
    def validate_new_name_field(cls, v):
        """Validate new scorer name"""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Name must contain only alphanumeric characters, underscores, and hyphens")
        return v

class ScorerUpdateRequest(BaseModel):
    """Request model for updating a scorer"""
    name: Optional[str] = Field(None, min_length=3, max_length=SecurityLimits.MAX_NAME_LENGTH, description="New name for scorer")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Updated parameters")
    
    @validator('name')
    def validate_name_field(cls, v):
        """Validate scorer name"""
        if v is not None:
            v = sanitize_string(v)
            if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
                raise ValueError("Name must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    @validator('parameters')
    def validate_parameters_field(cls, v):
        """Validate scorer parameters"""
        if v is not None:
            return validate_generator_parameters(v)
        return v

class ScorerInfo(BaseModel):
    """Information about a configured scorer"""
    id: str = Field(..., description="Unique scorer ID")
    name: str = Field(..., description="Scorer name")
    type: str = Field(..., description="Scorer type/class")
    category: str = Field(..., description="Scorer category")
    parameters: Dict[str, Any] = Field(..., description="Scorer parameters")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_tested: Optional[datetime] = Field(None, description="Last test timestamp")
    test_count: int = Field(default=0, description="Number of tests run")

# Response models
class ScorerTypesResponse(BaseModel):
    """Response model for available scorer types"""
    categories: Dict[str, ScorerCategoryInfo] = Field(..., description="Scorer categories and their info")
    available_scorers: List[str] = Field(..., description="All available scorer types")
    test_cases: Dict[str, List[str]] = Field(..., description="Test cases by category")

class ScorerParametersResponse(BaseModel):
    """Response model for scorer parameters"""
    scorer_type: str = Field(..., description="Scorer type")
    parameters: List[ScorerParameter] = Field(..., description="Parameter definitions")
    requires_target: bool = Field(..., description="Whether scorer requires chat_target")
    category: str = Field(..., description="Scorer category")
    description: str = Field(..., description="Scorer description")

class ScorersListResponse(BaseModel):
    """Response model for listing scorers"""
    scorers: List[ScorerInfo] = Field(..., description="List of configured scorers")
    total: int = Field(..., description="Total number of scorers")
    by_category: Dict[str, int] = Field(..., description="Count by category")

class ScorerDeleteResponse(BaseModel):
    """Response model for scorer deletion"""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Success or error message")
    deleted_scorer: str = Field(..., description="Name of deleted scorer")

# Bulk operations

# Error models
class ScorerError(BaseModel):
    """Error model for scorer operations"""
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    scorer_name: Optional[str] = Field(None, description="Scorer name if applicable")

# Utility models
class ScorerValidationRequest(BaseModel):
    """Request model for validating scorer configuration"""
    scorer_type: str = Field(..., min_length=3, max_length=100, description="Scorer type to validate")
    parameters: Dict[str, Any] = Field(..., description="Parameters to validate")
    generator_id: Optional[str] = Field(None, max_length=100, description="Generator ID if needed")
    
    @validator('scorer_type')
    def validate_scorer_type_field(cls, v):
        """Validate scorer type"""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Scorer type must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    @validator('parameters')
    def validate_parameters_field(cls, v):
        """Validate scorer parameters"""
        return validate_generator_parameters(v)
    
    @validator('generator_id')
    def validate_generator_id_field(cls, v):
        """Validate generator ID"""
        if v is not None:
            v = sanitize_string(v)
            if len(v) > 100:
                raise ValueError("Generator ID too long")
        return v

class ScorerValidationResponse(BaseModel):
    """Response model for scorer validation"""
    valid: bool = Field(..., description="Whether configuration is valid")
    errors: List[str] = Field(..., description="Validation errors")
    warnings: List[str] = Field(..., description="Validation warnings")
    suggested_fixes: List[str] = Field(..., description="Suggested fixes")

# Advanced operations
class ScorerAnalyticsRequest(BaseModel):
    """Request model for scorer analytics"""
    scorer_id: str = Field(..., max_length=100, description="Scorer ID")
    start_date: Optional[datetime] = Field(None, description="Start date for analytics")
    end_date: Optional[datetime] = Field(None, description="End date for analytics")
    
    @validator('scorer_id')
    def validate_scorer_id_field(cls, v):
        """Validate scorer ID"""
        v = sanitize_string(v)
        if len(v) > 100:
            raise ValueError("Scorer ID too long")
        return v

class ScorerAnalyticsResponse(BaseModel):
    """Response model for scorer analytics"""
    scorer_id: str = Field(..., description="Scorer ID")
    total_tests: int = Field(..., description="Total number of tests")
    success_rate: float = Field(..., description="Test success rate")
    average_score: Optional[float] = Field(None, description="Average score value")
    common_categories: List[str] = Field(..., description="Most common score categories")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")

# Export/Import models
class ScorerConfigExport(BaseModel):
    """Model for exporting scorer configurations"""
    scorers: List[ScorerInfo] = Field(..., description="Scorer configurations")
    export_date: datetime = Field(..., description="Export timestamp")
    version: str = Field(default="1.0", description="Export format version")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")

class ScorerConfigImport(BaseModel):
    """Model for importing scorer configurations"""
    scorers: List[Dict[str, Any]] = Field(..., max_items=50, description="Scorer configurations to import")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing scorers")
    validate_before_import: bool = Field(default=True, description="Validate before importing")
    
    @validator('scorers')
    def validate_scorers_field(cls, v):
        """Validate scorer configurations"""
        validated = []
        for scorer_config in v:
            if not isinstance(scorer_config, dict):
                raise ValueError("Scorer configuration must be a dictionary")
            
            # Validate the configuration structure
            if 'name' in scorer_config:
                scorer_config['name'] = sanitize_string(str(scorer_config['name']))
                if len(scorer_config['name']) > SecurityLimits.MAX_NAME_LENGTH:
                    raise ValueError("Scorer name too long")
            
            if 'parameters' in scorer_config and isinstance(scorer_config['parameters'], dict):
                scorer_config['parameters'] = validate_generator_parameters(scorer_config['parameters'])
            
            validated.append(scorer_config)
        return validated

class ScorerImportResponse(BaseModel):
    """Response model for scorer import"""
    success: bool = Field(..., description="Whether import was successful")
    imported_count: int = Field(..., description="Number of scorers imported")
    skipped_count: int = Field(..., description="Number of scorers skipped")
    errors: List[str] = Field(..., description="Import errors")
    imported_scorers: List[str] = Field(..., description="Names of imported scorers")

# Health and status models
class ScorerHealthResponse(BaseModel):
    """Response model for scorer health check"""
    healthy: bool = Field(..., description="Whether scorer system is healthy")
    total_scorers: int = Field(..., description="Total number of configured scorers")
    active_scorers: int = Field(..., description="Number of active/functional scorers")
    failed_scorers: List[str] = Field(..., description="Names of failed scorers")
    system_info: Dict[str, Any] = Field(..., description="System information")

