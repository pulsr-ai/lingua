from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"
    TOOL = "tool"  # For tool results


class MessageBase(BaseModel):
    role: MessageRole
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None  # For tool response messages
    name: Optional[str] = None
    # Keep backwards compatibility
    function_call: Optional[Dict[str, Any]] = None


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    id: UUID
    chat_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageSendRequest(BaseModel):
    content: str
    include_memories: bool = False
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None
    # Keep backwards compatibility
    functions: Optional[List[Dict[str, Any]]] = None


class MessageSendResponse(BaseModel):
    message: Message
    usage: Optional[Dict[str, int]] = None