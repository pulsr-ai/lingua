import logging
import json
from typing import Dict, Any, Optional, Generator, AsyncGenerator
import openai
from openai import OpenAI, AsyncOpenAI
from fastapi import HTTPException

from app.providers.base import BaseLLMProvider
from app.schemas.llm import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def default_model(self) -> str:
        return "gpt-3.5-turbo"
    
    def complete(self, request: LLMRequest) -> LLMResponse:
        logger.info(f"Making completion request to provider with model {request.model or self.default_model}")
        model = request.model or self.default_model
        
        kwargs = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        
        # Add tools if provided
        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
        
        try:
            logger.info("Sending request to OpenAI compatible API")
            response = self.client.chat.completions.create(**kwargs)
            logger.info("Received response from OpenAI compatible API")
        except openai.APIError as e:
            logger.error(f"OpenAI API Error: {e}")
            raise HTTPException(status_code=400, detail=f"OpenAI API Error: {e}")
        
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
        
        
        return LLMResponse(
            content=message.content,
            role=message.role,
            tool_calls=tool_calls,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if response.usage else None,
            model=response.model,
            provider=self.name
        )
    
    def stream(self, request: LLMRequest) -> Generator[str, None, None]:
        logger.info(f"Making stream request to provider with model {request.model or self.default_model}")
        model = request.model or self.default_model
        
        kwargs = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        
        # Add tools if provided
        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
        
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
        
        # Add tools if provided
        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
        
        try:
            response = await self.async_client.chat.completions.create(**kwargs)
        except openai.APIError as e:
            raise HTTPException(status_code=400, detail=f"OpenAI API Error: {e}")
        
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
        
        
        return LLMResponse(
            content=message.content,
            role=message.role,
            tool_calls=tool_calls,
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
        
        # Add tools if provided
        if request.tools:
            kwargs["tools"] = request.tools
            if request.tool_choice:
                kwargs["tool_choice"] = request.tool_choice
        
        stream = await self.async_client.chat.completions.create(**kwargs)
        
        tool_calls = {}  # Track tool calls across chunks
        
        async for chunk in stream:
            delta = chunk.choices[0].delta
            
            # Handle content
            if delta.content:
                yield delta.content
            
            # Handle tool calls in streaming
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                for tool_call_chunk in delta.tool_calls:
                    index = tool_call_chunk.index
                    
                    if index not in tool_calls:
                        tool_calls[index] = {
                            "id": "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                        }
                    
                    # Update tool call data
                    if tool_call_chunk.id:
                        tool_calls[index]["id"] = tool_call_chunk.id
                    
                    if tool_call_chunk.function:
                        if tool_call_chunk.function.name:
                            tool_calls[index]["function"]["name"] = tool_call_chunk.function.name
                        if tool_call_chunk.function.arguments:
                            tool_calls[index]["function"]["arguments"] += tool_call_chunk.function.arguments
        
        # If we collected tool calls, yield them at the end
        if tool_calls:
            yield json.dumps({
                "tool_calls": list(tool_calls.values())
            })