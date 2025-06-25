"""
Generator Factory for creating test generator instances

This module provides factory functions for creating generator test data
with realistic values for unit and integration tests.
"""
import factory
from factory import Faker, SubFactory, LazyAttribute, DictFactory
import uuid
from datetime import datetime
from typing import Dict, Any, Optional


class GeneratorParametersFactory(DictFactory):
    """Factory for generator parameters"""
    temperature = Faker('pyfloat', min_value=0.0, max_value=2.0, right_digits=1)
    max_tokens = Faker('pyint', min_value=100, max_value=4000)
    top_p = Faker('pyfloat', min_value=0.0, max_value=1.0, right_digits=2)
    frequency_penalty = Faker('pyfloat', min_value=-2.0, max_value=2.0, right_digits=1)
    presence_penalty = Faker('pyfloat', min_value=-2.0, max_value=2.0, right_digits=1)
    stop_sequences = factory.List([
        Faker('word'),
        Faker('word'),
    ])


class GeneratorFactory(factory.Factory):
    """Factory for creating test generators"""
    
    class Meta:
        model = dict
    
    id = factory.LazyFunction(lambda: f"gen-{uuid.uuid4()}")
    name = factory.Sequence(lambda n: f"Test Generator {n}")
    provider = factory.Iterator([
        "openai",
        "anthropic",
        "google",
        "azure",
        "ollama",
        "huggingface"
    ])
    model = factory.LazyAttribute(lambda obj: {
        "openai": factory.Iterator(["gpt-4", "gpt-3.5-turbo", "gpt-4o"]),
        "anthropic": factory.Iterator(["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]),
        "google": factory.Iterator(["gemini-pro", "gemini-1.5-pro"]),
        "azure": factory.Iterator(["gpt-4", "gpt-35-turbo"]),
        "ollama": factory.Iterator(["llama2", "mistral", "codellama"]),
        "huggingface": factory.Iterator(["meta-llama/Llama-2-7b", "mistralai/Mistral-7B"])
    }.get(obj.provider, factory.Iterator(["default-model"])))
    
    parameters = factory.SubFactory(GeneratorParametersFactory)
    is_active = True
    created_at = factory.Faker('date_time')
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)
    
    # Optional fields
    description = factory.Faker('sentence', nb_words=10)
    endpoint = factory.LazyAttribute(
        lambda obj: f"/ai/{obj.provider}/{obj.model.replace('.', '').replace('-', '')}"
    )
    api_key_required = factory.LazyAttribute(
        lambda obj: obj.provider not in ["ollama", "local"]
    )
    
    @factory.lazy_attribute
    def tags(self):
        """Generate relevant tags based on provider and model"""
        tags = [self.provider]
        if "gpt" in str(self.model).lower():
            tags.append("gpt")
        if "claude" in str(self.model).lower():
            tags.append("claude")
        if self.provider == "ollama":
            tags.append("local")
        return tags


class OpenAIGeneratorFactory(GeneratorFactory):
    """Factory specifically for OpenAI generators"""
    provider = "openai"
    model = factory.Iterator(["gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"])
    
    @factory.lazy_attribute
    def parameters(self):
        """OpenAI-specific parameters"""
        params = GeneratorParametersFactory()
        params.update({
            "model": self.model,
            "stream": False,
            "n": 1,
            "logprobs": False
        })
        return params


class AnthropicGeneratorFactory(GeneratorFactory):
    """Factory specifically for Anthropic generators"""
    provider = "anthropic"
    model = factory.Iterator([
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022"
    ])
    
    @factory.lazy_attribute
    def parameters(self):
        """Anthropic-specific parameters"""
        params = GeneratorParametersFactory()
        params.update({
            "model": self.model,
            "max_tokens": 4096,  # Anthropic supports larger context
            "stream": False
        })
        # Remove OpenAI-specific parameters
        params.pop('frequency_penalty', None)
        params.pop('presence_penalty', None)
        return params


class LocalGeneratorFactory(GeneratorFactory):
    """Factory for local/Ollama generators"""
    provider = "ollama"
    model = factory.Iterator(["llama2", "mistral", "codellama", "phi"])
    api_key_required = False
    
    @factory.lazy_attribute
    def endpoint(self):
        """Local endpoint for Ollama"""
        return f"http://localhost:11434/api/generate"
    
    @factory.lazy_attribute
    def parameters(self):
        """Ollama-specific parameters"""
        return {
            "temperature": 0.8,
            "top_p": 0.9,
            "num_predict": 128,
            "repeat_penalty": 1.1
        }


def create_test_generator(**kwargs) -> Dict[str, Any]:
    """
    Create a test generator with optional overrides
    
    Args:
        **kwargs: Override any generator attributes
    
    Returns:
        Dict containing generator data
    """
    return GeneratorFactory(**kwargs)


def create_openai_generator(**kwargs) -> Dict[str, Any]:
    """Create an OpenAI generator for testing"""
    return OpenAIGeneratorFactory(**kwargs)


def create_anthropic_generator(**kwargs) -> Dict[str, Any]:
    """Create an Anthropic generator for testing"""
    return AnthropicGeneratorFactory(**kwargs)


def create_local_generator(**kwargs) -> Dict[str, Any]:
    """Create a local/Ollama generator for testing"""
    return LocalGeneratorFactory(**kwargs)


def create_generator_batch(count: int = 5, **kwargs) -> list[Dict[str, Any]]:
    """
    Create multiple test generators
    
    Args:
        count: Number of generators to create
        **kwargs: Override attributes for all generators
    
    Returns:
        List of generator dictionaries
    """
    return GeneratorFactory.create_batch(count, **kwargs)


def create_diverse_generators() -> list[Dict[str, Any]]:
    """Create a diverse set of generators for comprehensive testing"""
    return [
        create_openai_generator(name="OpenAI GPT-4"),
        create_openai_generator(name="OpenAI GPT-3.5", model="gpt-3.5-turbo"),
        create_anthropic_generator(name="Claude 3 Opus"),
        create_anthropic_generator(name="Claude 3 Sonnet", model="claude-3-sonnet-20240229"),
        create_local_generator(name="Local Llama 2"),
        create_local_generator(name="Local Mistral", model="mistral"),
        create_test_generator(provider="google", model="gemini-pro", name="Google Gemini"),
        create_test_generator(provider="azure", model="gpt-4", name="Azure OpenAI"),
    ]