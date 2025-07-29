from typing import Dict, Any, Optional, Generator, AsyncGenerator, List
import httpx
import json

from app.providers.base import BaseLLMProvider
from app.schemas.llm import LLMRequest, LLMResponse


class LocalProvider(BaseLLMProvider):
    """Local LLM provider (e.g., Ollama, llama.cpp server)"""
    
    def __init__(self, endpoint: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.endpoint = endpoint.rstrip('/')
    
    @property
    def name(self) -> str:
        return "local"
    
    @property
    def default_model(self) -> str:
        return "llama2"
    
    def complete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        
        # Format for Ollama-style API
        payload = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "stream": False,
        }
        
        if request.max_tokens:
            payload["options"] = {"num_predict": request.max_tokens}
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.endpoint}/api/chat",
                json=payload,
                timeout=300.0
            )
            response.raise_for_status()
            data = response.json()
        
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            role="assistant",
            function_call=None,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            } if "eval_count" in data else None,
            model=model,
            provider=self.name
        )
    
    def stream(self, request: LLMRequest) -> Generator[str, None, None]:
        model = request.model or self.default_model
        
        payload = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            payload["options"] = {"num_predict": request.max_tokens}
        
        with httpx.Client() as client:
            with client.stream(
                "POST",
                f"{self.endpoint}/api/chat",
                json=payload,
                timeout=300.0
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
    
    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        
        payload = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "stream": False,
        }
        
        if request.max_tokens:
            payload["options"] = {"num_predict": request.max_tokens}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/api/chat",
                json=payload,
                timeout=300.0
            )
            response.raise_for_status()
            data = response.json()
        
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            role="assistant",
            function_call=None,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            } if "eval_count" in data else None,
            model=model,
            provider=self.name
        )
    
    async def astream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        model = request.model or self.default_model
        
        payload = {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "stream": True,
        }
        
        if request.max_tokens:
            payload["options"] = {"num_predict": request.max_tokens}
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.endpoint}/api/chat",
                json=payload,
                timeout=300.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]