from typing import Dict, Any, Optional, Generator, AsyncGenerator
import openai
from openai import OpenAI, AsyncOpenAI

from app.providers.base import BaseLLMProvider
from app.schemas.llm import LLMRequest, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider"""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = OpenAI(api_key=api_key)
        self.async_client = AsyncOpenAI(api_key=api_key)
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def default_model(self) -> str:
        return "gpt-3.5-turbo"
    
    def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        
        kwargs = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        
        # Use new tools format if available, fallback to functions for backwards compatibility
        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
        elif request.functions:
            kwargs["functions"] = request.functions
            if request.function_call:
                kwargs["function_call"] = request.function_call
        
        response = self.client.chat.completions.create(**kwargs)
        
        message = response.choices[0].message
        
        # Handle tool calls (new format)
        tool_calls = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_calls = [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
                for tool_call in message.tool_calls
            ]
        
        # Handle legacy function calls for backwards compatibility
        function_call = None
        if hasattr(message, 'function_call') and message.function_call:
            function_call = message.function_call.model_dump()
        
        return LLMResponse(
            content=message.content,
            role=message.role,
            tool_calls=tool_calls,
            function_call=function_call,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            model=response.model,
            provider=self.name
        )
    
    def stream(self, request: LLMRequest) -> Generator[str, None, None]:
        model = request.model or self.default_model
        
        kwargs = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        
        # Use new tools format if available, fallback to functions for backwards compatibility
        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
        elif request.functions:
            kwargs["functions"] = request.functions
            if request.function_call:
                kwargs["function_call"] = request.function_call
        
        stream = self.client.chat.completions.create(**kwargs)
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        
        kwargs = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        
        # Use new tools format if available, fallback to functions for backwards compatibility
        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
        elif request.functions:
            kwargs["functions"] = request.functions
            if request.function_call:
                kwargs["function_call"] = request.function_call
        
        response = await self.async_client.chat.completions.create(**kwargs)
        
        message = response.choices[0].message
        
        # Handle tool calls (new format)
        tool_calls = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_calls = [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
                for tool_call in message.tool_calls
            ]
        
        # Handle legacy function calls for backwards compatibility
        function_call = None
        if hasattr(message, 'function_call') and message.function_call:
            function_call = message.function_call.model_dump()
        
        return LLMResponse(
            content=message.content,
            role=message.role,
            tool_calls=tool_calls,
            function_call=function_call,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            model=response.model,
            provider=self.name
        )
    
    async def astream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        model = request.model or self.default_model
        
        kwargs = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        
        # Use new tools format if available, fallback to functions for backwards compatibility
        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
        elif request.functions:
            kwargs["functions"] = request.functions
            if request.function_call:
                kwargs["function_call"] = request.function_call
        
        stream = await self.async_client.chat.completions.create(**kwargs)
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content