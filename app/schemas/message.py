from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"  # For tool results


class MessageBase(BaseModel):
    role: MessageRole
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None  # For tool response messages
    name: Optional[str] = None
    enabled_functions: Optional[List[str]] = None  # Functions that were enabled for this message
    enabled_mcp_tools: Optional[List[str]] = None  # MCP tools that were enabled for this message


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
    provider_name: Optional[str] = None
    model: Optional[str] = None
    include_memories: bool = False
    # Tool selection (by default all available tools are included)
    enabled_functions: Optional[List[str]] = None  # List of function names to enable
    disabled_functions: Optional[List[str]] = None  # List of function names to disable
    enabled_mcp_tools: Optional[List[str]] = None  # List of MCP tool names to enable
    disabled_mcp_tools: Optional[List[str]] = None  # List of MCP tool names to disable
    tool_choice: Optional[str] = None


class MessageSendResponse(BaseModel):
    message: Message
    usage: Optional[Dict[str, int]] = None