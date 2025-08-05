from typing import Optional
from app.providers.base import BaseLLMProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.local_provider import LocalProvider
from app.core.config import settings


class LLMProviderFactory:
    """Factory for creating LLM provider instances"""
    
    @staticmethod
    def create_provider(
        provider_name: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """Create an LLM provider instance"""
        
        provider_name = provider_name or settings.default_llm_provider
        
        if provider_name == "openai":
            api_key = kwargs.get("api_key") or settings.openai_api_key
            base_url = kwargs.get("base_url") or settings.openai_api_base_url
            if not api_key:
                raise ValueError("OpenAI API key not provided")
            return OpenAIProvider(api_key=api_key, base_url=base_url, **kwargs)
        
        elif provider_name == "anthropic":
            api_key = kwargs.get("api_key") or settings.anthropic_api_key
            if not api_key:
                raise ValueError("Anthropic API key not provided")
            return AnthropicProvider(api_key=api_key, **kwargs)
        
        elif provider_name == "local":
            endpoint = kwargs.get("endpoint") or settings.local_llm_endpoint
            if not endpoint:
                raise ValueError("Local LLM endpoint not provided")
            return LocalProvider(endpoint=endpoint, **kwargs)
        
        elif provider_name == "private":
            endpoint = kwargs.get("endpoint") or settings.private_cloud_endpoint
            api_key = kwargs.get("api_key") or settings.private_cloud_api_key
            if not endpoint:
                raise ValueError("Private cloud endpoint not provided")
            # Private cloud could use OpenAI-compatible API
            return OpenAIProvider(api_key=api_key, base_url=endpoint, **kwargs)
        
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    @staticmethod
    def get_default_provider() -> BaseLLMProvider:
        """Get the default provider instance"""
        return LLMProviderFactory.create_provider()