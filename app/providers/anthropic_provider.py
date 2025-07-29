from typing import Dict, Any, Optional, Generator, AsyncGenerator, List
import anthropic
from anthropic import Anthropic, AsyncAnthropic

from app.providers.base import BaseLLMProvider
from app.schemas.llm import LLMRequest, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def default_model(self) -> str:
        return "claude-3-sonnet-20240229"
    
    def _convert_messages(self, messages: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
        """Convert OpenAI format messages to Anthropic format"""
        system_prompt = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        return system_prompt, anthropic_messages
    
    def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        system_prompt, messages = self._convert_messages(request.messages)
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 1024,
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = self.client.messages.create(**kwargs)
        
        content = ""
        if response.content:
            content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
        
        return LLMResponse(
            content=content,
            role="assistant",
            function_call=None,  # Anthropic doesn't support function calling in the same way
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            } if hasattr(response, 'usage') else None,
            model=response.model,
            provider=self.name
        )
    
    def stream(self, request: LLMRequest) -> Generator[str, None, None]:
        model = request.model or self.default_model
        system_prompt, messages = self._convert_messages(request.messages)
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 1024,
            "stream": True,
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text
    
    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        system_prompt, messages = self._convert_messages(request.messages)
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 1024,
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = await self.async_client.messages.create(**kwargs)
        
        content = ""
        if response.content:
            content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
        
        return LLMResponse(
            content=content,
            role="assistant",
            function_call=None,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            } if hasattr(response, 'usage') else None,
            model=response.model,
            provider=self.name
        )
    
    async def astream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        model = request.model or self.default_model
        system_prompt, messages = self._convert_messages(request.messages)
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 1024,
            "stream": True,
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        async with self.async_client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text