from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID

from app.schemas.message import Message


class ChatBase(BaseModel):
    title: Optional[str] = None
    system_message: Optional[str] = None
    enabled_functions: Optional[List[str]] = None  # Default enabled function names
    enabled_mcp_tools: Optional[List[str]] = None  # Default enabled MCP tool names


class ChatCreate(ChatBase):
    pass


class ChatUpdate(ChatBase):
    title: Optional[str] = None


class Chat(ChatBase):
    id: UUID
    subtenant_id: UUID
    created_at: datetime
    updated_at: datetime
    system_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class ChatWithMessages(Chat):
    messages: List[Message] = []