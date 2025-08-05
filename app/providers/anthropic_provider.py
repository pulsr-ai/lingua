from typing import Dict, Any, Optional, Generator, AsyncGenerator, List
import anthropic
from anthropic import Anthropic, AsyncAnthropic
import json

from app.providers.base import BaseLLMProvider
from app.schemas.llm import LLMRequest, LLMResponse, ToolCall


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
            elif msg["role"] == "tool":
                # Convert tool response to Anthropic format
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": msg["content"]
                    }]
                })
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                # Convert assistant message with tool calls
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                
                for tool_call in msg["tool_calls"]:
                    content.append({
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["function"]["name"],
                        "input": json.loads(tool_call["function"]["arguments"])
                    })
                
                anthropic_messages.append({
                    "role": "assistant",
                    "content": content
                })
            else:
                # Regular user/assistant messages
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        return system_prompt, anthropic_messages
    
    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI tools format to Anthropic tools format"""
        if not tools:
            return None
        
        anthropic_tools = []
        for tool in tools:
            if tool["type"] == "function":
                anthropic_tools.append({
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"]
                })
        
        return anthropic_tools if anthropic_tools else None
    
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
        
        # Add tools if provided
        if request.tools:
            anthropic_tools = self._convert_tools(request.tools)
            if anthropic_tools:
                kwargs["tools"] = anthropic_tools
        
        response = self.client.messages.create(**kwargs)
        
        # Process response content and tool calls
        content = ""
        tool_calls = None
        
        if response.content:
            text_parts = []
            tool_call_parts = []
            
            for block in response.content:
                if hasattr(block, 'type'):
                    if block.type == 'text':
                        text_parts.append(block.text)
                    elif block.type == 'tool_use':
                        tool_call_parts.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input)
                            }
                        })
                else:
                    # Fallback for simple text responses
                    text_parts.append(str(block))
            
            content = ''.join(text_parts)
            if tool_call_parts:
                tool_calls = [ToolCall(**tc) for tc in tool_call_parts]
        
        return LLMResponse(
            content=content if content else None,
            role="assistant",
            tool_calls=tool_calls,
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
        
        # Add tools if provided
        if request.tools:
            anthropic_tools = self._convert_tools(request.tools)
            if anthropic_tools:
                kwargs["tools"] = anthropic_tools
        
        response = await self.async_client.messages.create(**kwargs)
        
        # Process response content and tool calls
        content = ""
        tool_calls = None
        
        if response.content:
            text_parts = []
            tool_call_parts = []
            
            for block in response.content:
                if hasattr(block, 'type'):
                    if block.type == 'text':
                        text_parts.append(block.text)
                    elif block.type == 'tool_use':
                        tool_call_parts.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": json.dumps(block.input)
                            }
                        })
                else:
                    # Fallback for simple text responses
                    text_parts.append(str(block))
            
            content = ''.join(text_parts)
            if tool_call_parts:
                tool_calls = [ToolCall(**tc) for tc in tool_call_parts]
        
        return LLMResponse(
            content=content if content else None,
            role="assistant",
            tool_calls=tool_calls,
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