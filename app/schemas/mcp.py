from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class MCPServerRequest(BaseModel):
    name: str
    url: str
    protocol: str = "websocket"
    api_key: Optional[str] = None


class MCPServerResponse(BaseModel):
    id: UUID
    name: str
    url: str
    protocol: str
    is_active: bool
    connection_status: str
    last_connected: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MCPToolResponse(BaseModel):
    name: str
    description: str
    server: str
    parameters: Dict[str, Any]


class MCPToolExecuteRequest(BaseModel):
    arguments: Dict[str, Any]


class MCPToolExecuteResponse(BaseModel):
    result: Any


class UpdateMCPServerRequest(BaseModel):
    url: Optional[str] = None
    protocol: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None