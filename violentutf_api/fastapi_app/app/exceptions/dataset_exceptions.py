"""
Custom exceptions for dataset import operations

This module provides specialized exception classes for different types
of dataset import failures, enabling more precise error handling and reporting.
"""

from typing import Any, Dict, Optional


class DatasetImportBaseException(Exception):
    """Base exception for all dataset import related errors"""
    
    def __init__(
        self, 
        message: str, 
        dataset_id: Optional[str] = None,
        dataset_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.dataset_id = dataset_id
        self.dataset_type = dataset_type
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "dataset_id": self.dataset_id,
            "dataset_type": self.dataset_type,
            "context": self.context
        }


class DatasetConfigurationError(DatasetImportBaseException):
    """Raised when dataset configuration is invalid or missing"""
    pass


class DatasetNotFoundError(DatasetImportBaseException):
    """Raised when requested dataset cannot be found"""
    pass


class DatasetStreamingError(DatasetImportBaseException):
    """Raised when streaming operations fail"""
    
    def __init__(
        self, 
        message: str, 
        chunk_index: Optional[int] = None,
        total_chunks: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks
        })
        return result


class DatasetMemoryError(DatasetImportBaseException):
    """Raised when PyRIT memory operations fail"""
    
    def __init__(
        self, 
        message: str, 
        memory_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.memory_path = memory_path
        self.operation = operation
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "memory_path": self.memory_path,
            "operation": self.operation
        })
        return result


class DatasetValidationError(DatasetImportBaseException):
    """Raised when dataset content validation fails"""
    
    def __init__(
        self, 
        message: str, 
        validation_errors: Optional[list] = None,
        prompt_index: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []
        self.prompt_index = prompt_index
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "validation_errors": self.validation_errors,
            "prompt_index": self.prompt_index
        })
        return result


class DatasetRetryExhaustedException(DatasetImportBaseException):
    """Raised when maximum retry attempts are exceeded"""
    
    def __init__(
        self, 
        message: str, 
        max_retries: int,
        last_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.max_retries = max_retries
        self.last_error = last_error
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "max_retries": self.max_retries,
            "last_error": str(self.last_error) if self.last_error else None
        })
        return result


class DatasetConcurrencyError(DatasetImportBaseException):
    """Raised when concurrent import limits are exceeded"""
    
    def __init__(
        self, 
        message: str, 
        active_imports: int,
        max_concurrent: int,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.active_imports = active_imports
        self.max_concurrent = max_concurrent
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "active_imports": self.active_imports,
            "max_concurrent": self.max_concurrent
        })
        return result


class DatasetStorageError(DatasetImportBaseException):
    """Raised when storage operations fail"""
    
    def __init__(
        self, 
        message: str, 
        storage_type: Optional[str] = None,
        storage_path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.storage_type = storage_type
        self.storage_path = storage_path
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "storage_type": self.storage_type,
            "storage_path": self.storage_path
        })
        return result


class DatasetTimeoutError(DatasetImportBaseException):
    """Raised when operations exceed timeout limits"""
    
    def __init__(
        self, 
        message: str, 
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.operation = operation
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "timeout_seconds": self.timeout_seconds,
            "operation": self.operation
        })
        return result


# Exception mapping for HTTP status codes
EXCEPTION_STATUS_MAPPING = {
    DatasetConfigurationError: 400,
    DatasetNotFoundError: 404,
    DatasetValidationError: 422,
    DatasetConcurrencyError: 429,
    DatasetTimeoutError: 408,
    DatasetStreamingError: 500,
    DatasetMemoryError: 500,
    DatasetStorageError: 500,
    DatasetRetryExhaustedException: 503,
    DatasetImportBaseException: 500,
}


def get_http_status_for_exception(exception: Exception) -> int:
    """Get appropriate HTTP status code for a dataset exception"""
    for exc_type, status_code in EXCEPTION_STATUS_MAPPING.items():
        if isinstance(exception, exc_type):
            return status_code
    return 500  # Default to internal server error