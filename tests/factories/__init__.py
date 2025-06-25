"""
Test Data Factories

This module provides factory functions for creating test data instances
for use in unit and integration tests.
"""

from .generator_factory import (
    GeneratorFactory,
    OpenAIGeneratorFactory,
    AnthropicGeneratorFactory,
    LocalGeneratorFactory,
    create_test_generator,
    create_openai_generator,
    create_anthropic_generator,
    create_local_generator,
    create_generator_batch,
    create_diverse_generators
)

from .user_factory import (
    UserFactory,
    AdminUserFactory,
    DeveloperUserFactory,
    APIUserFactory,
    JWTTokenFactory,
    KeycloakTokenFactory,
    create_test_user,
    create_admin_user,
    create_developer_user,
    create_api_user,
    create_jwt_token,
    create_expired_token,
    create_keycloak_token_response,
    create_user_batch,
    create_diverse_users,
    create_authenticated_request_headers
)

from .dataset_factory import (
    PromptFactory,
    DatasetFactory,
    SecurityDatasetFactory,
    BenchmarkDatasetFactory,
    CSVDatasetFactory,
    create_test_dataset,
    create_security_dataset,
    create_benchmark_dataset,
    create_csv_dataset,
    create_dataset_batch,
    create_prompt_batch,
    create_diverse_datasets,
    create_garak_dataset,
    create_pyrit_dataset
)

__all__ = [
    # Generator factories
    'GeneratorFactory',
    'OpenAIGeneratorFactory',
    'AnthropicGeneratorFactory',
    'LocalGeneratorFactory',
    'create_test_generator',
    'create_openai_generator',
    'create_anthropic_generator',
    'create_local_generator',
    'create_generator_batch',
    'create_diverse_generators',
    
    # User factories
    'UserFactory',
    'AdminUserFactory',
    'DeveloperUserFactory',
    'APIUserFactory',
    'JWTTokenFactory',
    'KeycloakTokenFactory',
    'create_test_user',
    'create_admin_user',
    'create_developer_user',
    'create_api_user',
    'create_jwt_token',
    'create_expired_token',
    'create_keycloak_token_response',
    'create_user_batch',
    'create_diverse_users',
    'create_authenticated_request_headers',
    
    # Dataset factories
    'PromptFactory',
    'DatasetFactory',
    'SecurityDatasetFactory',
    'BenchmarkDatasetFactory',
    'CSVDatasetFactory',
    'create_test_dataset',
    'create_security_dataset',
    'create_benchmark_dataset',
    'create_csv_dataset',
    'create_dataset_batch',
    'create_prompt_batch',
    'create_diverse_datasets',
    'create_garak_dataset',
    'create_pyrit_dataset'
]