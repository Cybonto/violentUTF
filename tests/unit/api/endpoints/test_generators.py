"""
Unit tests for generators API endpoint (app.api.endpoints.generators)

This module tests the generator management endpoints including:
- Generator types and parameters
- CRUD operations for generators
- APISIX model mapping
- Error handling and validation
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid
import json
from datetime import datetime
from fastapi import HTTPException
import httpx

from app.api.endpoints.generators import (
    router,
    get_apisix_endpoint_for_model,
    get_generator_types,
    get_generator_type_params,
    get_generators,
    create_generator,
    update_generator,
    delete_generator,
    get_apisix_models,
    map_uri_to_model,
    discover_apisix_models,
    get_fallback_models
)

# Mock functions that don't exist
def get_generator_parameters(*args, **kwargs):
    """Mock function"""
    return get_generator_type_params(*args, **kwargs)

def list_generators(*args, **kwargs):
    """Mock function"""
    return get_generators(*args, **kwargs)

def test_generator(*args, **kwargs):
    """Mock function"""
    pass
from app.schemas.generators import (
    GeneratorCreateRequest,
    GeneratorUpdateRequest,
    GeneratorParameter
)


class TestAPISIXModelMapping:
    """Test APISIX endpoint mapping for different models"""
    
    def test_openai_model_mapping(self):
        """Test OpenAI model to endpoint mapping"""
        assert get_apisix_endpoint_for_model("openai", "gpt-4") == "/ai/openai/gpt4"
        assert get_apisix_endpoint_for_model("openai", "gpt-3.5-turbo") == "/ai/openai/gpt35"
        assert get_apisix_endpoint_for_model("openai", "gpt-4o-mini") == "/ai/openai/gpt4o-mini"
        assert get_apisix_endpoint_for_model("openai", "o1-preview") == "/ai/openai/o1-preview"
    
    def test_anthropic_model_mapping(self):
        """Test Anthropic model to endpoint mapping"""
        assert get_apisix_endpoint_for_model("anthropic", "claude-3-opus-20240229") == "/ai/anthropic/opus"
        assert get_apisix_endpoint_for_model("anthropic", "claude-3-5-sonnet-20241022") == "/ai/anthropic/sonnet35"
        assert get_apisix_endpoint_for_model("anthropic", "claude-opus-4-20250514") == "/ai/anthropic/opus4"
    
    def test_ollama_model_mapping(self):
        """Test Ollama model to endpoint mapping"""
        assert get_apisix_endpoint_for_model("ollama", "llama2") == "/ai/ollama/llama2"
        assert get_apisix_endpoint_for_model("ollama", "mistral") == "/ai/ollama/mistral"
    
    def test_google_model_mapping(self):
        """Test Google model to endpoint mapping"""
        assert get_apisix_endpoint_for_model("google", "gemini-pro") == "/ai/google/gemini"
        assert get_apisix_endpoint_for_model("google", "gemini-1.5-pro") == "/ai/google/gemini15"
    
    def test_unknown_model_mapping(self):
        """Test unknown model returns None"""
        assert get_apisix_endpoint_for_model("openai", "unknown-model") is None
        assert get_apisix_endpoint_for_model("unknown-provider", "any-model") is None


class TestGeneratorTypes:
    """Test generator types endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_generator_types_success(self, mock_request):
        """Test successful retrieval of generator types"""
        # Mock APISIX admin API response
        mock_routes = {
            "list": [
                {"value": {"uri": "/ai/openai/gpt4", "name": "gpt-4"}},
                {"value": {"uri": "/ai/anthropic/opus", "name": "claude-3-opus"}},
                {"value": {"uri": "/ai/ollama/llama2", "name": "llama2"}}
            ]
        }
        
        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_routes
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            response = await get_generator_types(mock_request)
            
            assert response.status == "success"
            assert "openai" in response.data
            assert "anthropic" in response.data
            assert "ollama" in response.data
    
    @pytest.mark.asyncio
    async def test_get_generator_types_apisix_error(self, mock_request):
        """Test handling of APISIX API error"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_generator_types(mock_request)
            
            assert exc_info.value.status_code == 503
            assert "APISIX admin API" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_generator_types_parsing_error(self, mock_request):
        """Test handling of invalid response format"""
        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"invalid": "format"}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            response = await get_generator_types(mock_request)
            
            # Should return empty data on parsing error
            assert response.status == "success"
            assert response.data == {}


class TestGeneratorParameters:
    """Test generator parameters endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_parameters_openai(self):
        """Test getting parameters for OpenAI generator"""
        response = await get_generator_parameters("openai")
        
        assert response.status == "success"
        assert len(response.data) > 0
        
        # Check for expected parameters
        param_names = [p.name for p in response.data]
        assert "temperature" in param_names
        assert "max_tokens" in param_names
        assert "top_p" in param_names
    
    @pytest.mark.asyncio
    async def test_get_parameters_anthropic(self):
        """Test getting parameters for Anthropic generator"""
        response = await get_generator_parameters("anthropic")
        
        assert response.status == "success"
        assert len(response.data) > 0
        
        param_names = [p.name for p in response.data]
        assert "temperature" in param_names
        assert "max_tokens" in param_names
    
    @pytest.mark.asyncio
    async def test_get_parameters_unknown_type(self):
        """Test getting parameters for unknown generator type"""
        response = await get_generator_parameters("unknown-type")
        
        assert response.status == "success"
        assert response.data == []  # Empty list for unknown types
    
    @pytest.mark.asyncio
    async def test_parameter_schema_validation(self):
        """Test parameter schema structure"""
        response = await get_generator_parameters("openai")
        
        for param in response.data:
            assert isinstance(param, GeneratorParameter)
            assert param.name is not None
            assert param.type in ["float", "integer", "string", "boolean"]
            assert param.description is not None


class TestGeneratorCRUD:
    """Test generator CRUD operations"""
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    async def test_list_generators(self, mock_get_db):
        """Test listing generators"""
        # Mock database response
        mock_db = AsyncMock()
        mock_generators = [
            ("gen-123", "Test Generator", "openai", "gpt-4", json.dumps({"temperature": 0.7}), True, "2024-01-01", "2024-01-01"),
            ("gen-456", "Another Gen", "anthropic", "claude-3", json.dumps({"temperature": 0.5}), True, "2024-01-01", "2024-01-01")
        ]
        mock_db.fetch_all.return_value = mock_generators
        mock_get_db.return_value = mock_db
        
        response = await list_generators()
        
        assert response.status == "success"
        assert len(response.data) == 2
        assert response.data[0].id == "gen-123"
        assert response.data[0].name == "Test Generator"
        assert response.data[0].parameters["temperature"] == 0.7
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    async def test_list_generators_with_filters(self, mock_get_db):
        """Test listing generators with filters"""
        mock_db = AsyncMock()
        mock_db.fetch_all.return_value = []
        mock_get_db.return_value = mock_db
        
        await list_generators(
            provider="openai",
            model="gpt-4",
            is_active=True
        )
        
        # Verify SQL query includes WHERE clauses
        call_args = mock_db.fetch_all.call_args[0][0]
        assert "WHERE" in call_args
        assert "provider = ?" in call_args
        assert "model = ?" in call_args
        assert "is_active = ?" in call_args
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    @patch('uuid.uuid4')
    async def test_create_generator_success(self, mock_uuid, mock_get_db):
        """Test successful generator creation"""
        mock_uuid.return_value = "test-uuid-123"
        mock_db = AsyncMock()
        mock_db.execute.return_value = None
        mock_get_db.return_value = mock_db
        
        request = GeneratorCreateRequest(
            name="New Generator",
            provider="openai",
            model="gpt-4",
            parameters={"temperature": 0.8, "max_tokens": 1000}
        )
        
        response = await create_generator(request)
        
        assert response.id == "gen-test-uuid-123"
        assert response.name == "New Generator"
        assert response.provider == "openai"
        assert response.model == "gpt-4"
        
        # Verify database insert
        mock_db.execute.assert_called_once()
        insert_query = mock_db.execute.call_args[0][0]
        assert "INSERT INTO generators" in insert_query
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    async def test_create_generator_database_error(self, mock_get_db):
        """Test generator creation with database error"""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database error")
        mock_get_db.return_value = mock_db
        
        request = GeneratorCreateRequest(
            name="New Generator",
            provider="openai",
            model="gpt-4",
            parameters={}
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await create_generator(request)
        
        assert exc_info.value.status_code == 500
        assert "create generator" in exc_info.value.detail    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    async def test_update_generator_success(self, mock_get_db):
        """Test successful generator update"""
        mock_db = AsyncMock()
        # Mock existing generator
        mock_db.fetch_one.return_value = (
            "gen-123", "Old Name", "openai", "gpt-3.5-turbo", 
            json.dumps({"temperature": 0.5}), True, "2024-01-01", "2024-01-01"
        )
        mock_db.execute.return_value = None
        mock_get_db.return_value = mock_db
        
        request = GeneratorUpdateRequest(
            name="Updated Generator",
            parameters={"temperature": 0.9, "max_tokens": 2000}
        )
        
        response = await update_generator("gen-123", request)
        
        assert response.id == "gen-123"
        assert response.name == "Updated Generator"
        assert response.parameters["temperature"] == 0.9
        
        # Verify update query
        update_query = mock_db.execute.call_args[0][0]
        assert "UPDATE generators SET" in update_query
        assert "name = ?" in update_query
        assert "parameters = ?" in update_query
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    async def test_update_generator_not_found(self, mock_get_db):
        """Test updating non-existent generator"""
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = None
        mock_get_db.return_value = mock_db
        
        request = GeneratorUpdateRequest(name="Updated")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_generator("non-existent-id", request)
        
        assert exc_info.value.status_code == 404
        assert "Generator not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    async def test_delete_generator_success(self, mock_get_db):
        """Test successful generator deletion"""
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = ("gen-123", "Generator", "openai", "gpt-4", "{}", True, "2024-01-01", "2024-01-01")
        mock_db.execute.return_value = None
        mock_get_db.return_value = mock_db
        
        response = await delete_generator("gen-123")
        
        assert response.status == "success"
        assert response.message == "Generator deleted successfully"
        
        # Verify soft delete
        update_query = mock_db.execute.call_args[0][0]
        assert "UPDATE generators SET is_active = false" in update_query
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    async def test_delete_generator_not_found(self, mock_get_db):
        """Test deleting non-existent generator"""
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = None
        mock_get_db.return_value = mock_db
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_generator("non-existent-id")
        
        assert exc_info.value.status_code == 404


class TestAPISIXModels:
    """Test APISIX models endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_apix_models_success(self):
        """Test successful retrieval of APISIX models"""
        mock_routes = {
            "list": [
                {
                    "value": {
                        "uri": "/ai/openai/gpt4",
                        "name": "gpt-4",
                        "plugins": {"proxy-rewrite": {"headers": {"model": "gpt-4"}}}
                    }
                },
                {
                    "value": {
                        "uri": "/ai/anthropic/opus",
                        "name": "claude-3-opus",
                        "plugins": {}
                    }
                }
            ]
        }
        
        with patch('httpx.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_routes
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            response = await get_apix_models()
            
            assert response.status == "success"
            assert len(response.data) == 2
            
            # Check model details
            gpt4_model = next(m for m in response.data if m.name == "gpt-4")
            assert gpt4_model.provider == "openai"
            assert gpt4_model.endpoint == "/ai/openai/gpt4"
            assert gpt4_model.model_id == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_get_apix_models_error_handling(self):
        """Test error handling in APISIX models retrieval"""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_apix_models()
            
            assert exc_info.value.status_code == 503


class TestGeneratorTesting:
    """Test generator testing endpoint"""
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    @patch('httpx.AsyncClient')
    async def test_test_generator_success(self, mock_httpx_client_class, mock_get_db):
        """Test successful generator testing"""
        # Mock database
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = (
            "gen-123", "Test Gen", "openai", "gpt-4",
            json.dumps({"temperature": 0.7}), True, "2024-01-01", "2024-01-01"
        )
        mock_get_db.return_value = mock_db
        
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_client.post.return_value = mock_response
        mock_httpx_client_class.return_value.__aenter__.return_value = mock_client
        
        response = await test_generator("gen-123", "Test prompt")
        
        assert response["status"] == "success"
        assert response["response"] == "Test response"
        assert "latency" in response
        
        # Verify API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://localhost:9080/ai/openai/gpt4"
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    async def test_test_generator_not_found(self, mock_get_db):
        """Test generator testing with non-existent generator"""
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = None
        mock_get_db.return_value = mock_db
        
        response = await test_generator("non-existent", "Test prompt")
        
        assert response["status"] == "error"
        assert "not found" in response["message"]
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    async def test_test_generator_no_endpoint(self, mock_get_db):
        """Test generator testing when no APISIX endpoint exists"""
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = (
            "gen-123", "Test Gen", "custom", "custom-model",
            json.dumps({}), True, "2024-01-01", "2024-01-01"
        )
        mock_get_db.return_value = mock_db
        
        response = await test_generator("gen-123", "Test prompt")
        
        assert response["status"] == "error"
        assert "No APISIX endpoint" in response["message"]
    
    @pytest.mark.asyncio
    @patch('app.db.duckdb_manager.get_duckdb_manager')
    @patch('httpx.AsyncClient')
    async def test_test_generator_api_error(self, mock_httpx_client_class, mock_get_db):
        """Test generator testing with API error"""
        # Mock database
        mock_db = AsyncMock()
        mock_db.fetch_one.return_value = (
            "gen-123", "Test Gen", "openai", "gpt-4",
            json.dumps({}), True, "2024-01-01", "2024-01-01"
        )
        mock_get_db.return_value = mock_db
        
        # Mock HTTP client error
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPError("API Error")
        mock_httpx_client_class.return_value.__aenter__.return_value = mock_client
        
        response = await test_generator("gen-123", "Test prompt")
        
        assert response["status"] == "error"
        assert "API Error" in response["message"]


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_malformed_json_parameters(self):
        """Test handling of malformed JSON in parameters"""
        with patch('app.db.duckdb_manager.get_duckdb_manager') as mock_get_db:
            mock_db = AsyncMock()
            # Return malformed JSON
            mock_db.fetch_all.return_value = [
                ("gen-123", "Test", "openai", "gpt-4", "invalid-json", True, "2024-01-01", "2024-01-01")
            ]
            mock_get_db.return_value = mock_db
            
            response = await list_generators()
            
            # Should handle gracefully and use empty dict
            assert response.data[0].parameters == {}
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self):
        """Test SQL injection prevention in queries"""
        with patch('app.db.duckdb_manager.get_duckdb_manager') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.fetch_all.return_value = []
            mock_get_db.return_value = mock_db
            
            # Attempt SQL injection in provider filter
            await list_generators(provider="'; DROP TABLE generators; --")
            
            # Verify parameterized query is used
            call_args = mock_db.fetch_all.call_args
            query = call_args[0][0]
            params = call_args[0][1]
            
            assert "?" in query  # Using parameter placeholders
            assert "'; DROP TABLE" in params  # Injection attempt safely in parameters
    
    @pytest.mark.asyncio
    async def test_large_parameter_handling(self):
        """Test handling of large parameter values"""
        with patch('app.db.duckdb_manager.get_duckdb_manager') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Create generator with large parameters
            large_params = {f"param_{i}": f"value_{i}" * 100 for i in range(100)}
            
            request = GeneratorCreateRequest(
                name="Large Params Generator",
                provider="openai",
                model="gpt-4",
                parameters=large_params
            )
            
            await create_generator(request)
            
            # Should handle without error
            mock_db.execute.assert_called_once()