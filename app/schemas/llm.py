from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel
from uuid import UUID


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Dict[str, Any]


class LLMRequest(BaseModel):
    messages: List[Dict[str, Any]]
    provider_name: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str | Dict[str, Any]] = None


class LLMResponse(BaseModel):
    content: Optional[str] = None
    role: str = "assistant"
    tool_calls: Optional[List[ToolCall]] = None
    usage: Optional[Dict[str, int]] = None
    model: str
    provider: str