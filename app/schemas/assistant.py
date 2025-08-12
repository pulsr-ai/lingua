from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class AssistantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Assistant name")
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    enabled_functions: Optional[List[str]] = None
    enabled_mcp_tools: Optional[List[str]] = None
    function_parameters: Optional[Dict[str, Any]] = None
    mcp_tool_parameters: Optional[Dict[str, Any]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Assistant name cannot be empty')
        return v.strip()


class AssistantCreate(AssistantBase):
    subtenant_id: Optional[UUID] = None  # If None, assistant is workspace-wide


class AssistantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    enabled_functions: Optional[List[str]] = None
    enabled_mcp_tools: Optional[List[str]] = None
    function_parameters: Optional[Dict[str, Any]] = None
    mcp_tool_parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Assistant(AssistantBase):
    id: UUID
    subtenant_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AssistantList(BaseModel):
    assistants: List[Assistant]
    total: int