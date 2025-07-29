from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class MCPServerRequest(BaseModel):
    name: str
    url: str
    protocol: str = "websocket"
    api_key: Optional[str] = None


class MCPServerResponse(BaseModel):
    name: str
    url: str
    protocol: str
    connected: bool


class MCPToolResponse(BaseModel):
    name: str
    description: str
    server: str
    parameters: Dict[str, Any]


class MCPToolExecuteRequest(BaseModel):
    arguments: Dict[str, Any]


class MCPToolExecuteResponse(BaseModel):
    result: Any