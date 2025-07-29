from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator, Generator
from app.schemas.llm import LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    """Base class for all LLM providers"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.config = kwargs
    
    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Synchronous completion"""
        pass
    
    @abstractmethod
    def stream(self, request: LLMRequest) -> Generator[str, None, None]:
        """Streaming completion"""
        pass
    
    @abstractmethod
    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        """Asynchronous completion"""
        pass
    
    @abstractmethod
    async def astream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Asynchronous streaming completion"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider"""
        pass