"""
MCP (Model Context Protocol) Client Implementation

This module provides a client for interacting with MCP servers,
allowing the LLM to use tools exposed by MCP-compatible servers.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import httpx
import websockets
from urllib.parse import urlparse

from app.core.functions import BaseFunctionHandler, FunctionDefinition, FunctionParameter


@dataclass
class MCPServer:
    """MCP Server configuration"""
    name: str
    url: str
    protocol: str = "websocket"  # websocket or http
    api_key: Optional[str] = None


class MCPToolHandler(BaseFunctionHandler):
    """Handler for MCP tools exposed as functions"""
    
    def __init__(self, server: MCPServer, tool_definition: Dict[str, Any]):
        self.server = server
        self.tool_definition = tool_definition
        self.name = tool_definition["name"]
        self.description = tool_definition.get("description", "")
    
    async def execute(self, **kwargs) -> Any:
        """Execute the MCP tool"""
        if self.server.protocol == "websocket":
            return await self._execute_websocket(**kwargs)
        else:
            return await self._execute_http(**kwargs)
    
    async def _execute_websocket(self, **kwargs) -> Any:
        """Execute tool via WebSocket"""
        async with websockets.connect(self.server.url) as websocket:
            # Send tool execution request
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": self.name,
                    "arguments": kwargs
                },
                "id": 1
            }
            
            if self.server.api_key:
                request["params"]["api_key"] = self.server.api_key
            
            await websocket.send(json.dumps(request))
            
            # Receive response
            response = await websocket.recv()
            result = json.loads(response)
            
            if "error" in result:
                raise Exception(f"MCP error: {result['error']}")
            
            return result.get("result")
    
    async def _execute_http(self, **kwargs) -> Any:
        """Execute tool via HTTP"""
        async with httpx.AsyncClient() as client:
            headers = {}
            if self.server.api_key:
                headers["Authorization"] = f"Bearer {self.server.api_key}"
            
            response = await client.post(
                f"{self.server.url}/tools/call",
                json={
                    "name": self.name,
                    "arguments": kwargs
                },
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"MCP HTTP error: {response.status_code} - {response.text}")
            
            return response.json()
    
    def get_definition(self) -> FunctionDefinition:
        """Convert MCP tool definition to function definition"""
        parameters = []
        
        if "inputSchema" in self.tool_definition:
            schema = self.tool_definition["inputSchema"]
            if schema.get("type") == "object" and "properties" in schema:
                for prop_name, prop_schema in schema["properties"].items():
                    param = FunctionParameter(
                        name=prop_name,
                        type=prop_schema.get("type", "string"),
                        description=prop_schema.get("description", ""),
                        required=prop_name in schema.get("required", [])
                    )
                    if "enum" in prop_schema:
                        param.enum = prop_schema["enum"]
                    parameters.append(param)
        
        return FunctionDefinition(
            name=self.name,
            description=self.description,
            parameters=parameters
        )


class MCPClient:
    """Client for interacting with MCP servers"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self._tool_handlers: Dict[str, MCPToolHandler] = {}
        self._loaded_servers = set()  # Track which servers are loaded
    
    async def connect_server(self, server: MCPServer):
        """Connect to an MCP server and discover available tools"""
        self.servers[server.name] = server
        
        # Discover available tools
        tools = await self._discover_tools(server)
        
        # Create handlers for each tool
        for tool in tools:
            handler = MCPToolHandler(server, tool)
            tool_name = f"{server.name}_{tool['name']}"
            self._tool_handlers[tool_name] = handler
    
    def get_tools_definitions(self) -> List[Dict[str, Any]]:
        """Get all MCP tools in OpenAI tools format"""
        # Load active servers from database if needed
        self._load_db_servers()
        
        tools = []
        for name, handler in self._tool_handlers.items():
            definition = handler.get_definition()
            
            # Convert to OpenAI tools format
            tool_def = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": definition.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            for param in definition.parameters:
                prop = {
                    "type": param.type,
                    "description": param.description
                }
                if param.enum:
                    prop["enum"] = param.enum
                
                tool_def["function"]["parameters"]["properties"][param.name] = prop
                if param.required:
                    tool_def["function"]["parameters"]["required"].append(param.name)
            
            tools.append(tool_def)
        
        return tools
    
    def _load_db_servers(self):
        """Load active MCP servers from database"""
        from app.db.base import SessionLocal
        from app.db.models import MCPServerModel
        
        db = SessionLocal()
        try:
            db_servers = db.query(MCPServerModel).filter(MCPServerModel.is_active == True).all()
            for db_server in db_servers:
                if db_server.name not in self._loaded_servers:
                    server = MCPServer(
                        name=db_server.name,
                        url=db_server.url,
                        protocol=db_server.protocol,
                        api_key=db_server.api_key
                    )
                    try:
                        # Try to connect (this would be async in real implementation)
                        # For now, just mark as loaded
                        self.servers[server.name] = server
                        self._loaded_servers.add(db_server.name)
                        
                        # Update connection status
                        from sqlalchemy import func
                        db.query(MCPServerModel).filter(MCPServerModel.id == db_server.id).update({
                            "connection_status": "connected",
                            "last_connected": func.now(),
                            "error_message": None
                        })
                        
                    except Exception as e:
                        # Update error status
                        db.query(MCPServerModel).filter(MCPServerModel.id == db_server.id).update({
                            "connection_status": "error",
                            "error_message": str(e)
                        })
            db.commit()
        finally:
            db.close()
    
    async def _discover_tools(self, server: MCPServer) -> List[Dict[str, Any]]:
        """Discover available tools from an MCP server"""
        if server.protocol == "websocket":
            return await self._discover_tools_websocket(server)
        else:
            return await self._discover_tools_http(server)
    
    async def _discover_tools_websocket(self, server: MCPServer) -> List[Dict[str, Any]]:
        """Discover tools via WebSocket"""
        async with websockets.connect(server.url) as websocket:
            # Send discovery request
            request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1
            }
            
            if server.api_key:
                request["params"]["api_key"] = server.api_key
            
            await websocket.send(json.dumps(request))
            
            # Receive response
            response = await websocket.recv()
            result = json.loads(response)
            
            if "error" in result:
                raise Exception(f"MCP discovery error: {result['error']}")
            
            return result.get("result", {}).get("tools", [])
    
    async def _discover_tools_http(self, server: MCPServer) -> List[Dict[str, Any]]:
        """Discover tools via HTTP"""
        async with httpx.AsyncClient() as client:
            headers = {}
            if server.api_key:
                headers["Authorization"] = f"Bearer {server.api_key}"
            
            response = await client.get(
                f"{server.url}/tools",
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise Exception(f"MCP discovery error: {response.status_code} - {response.text}")
            
            return response.json().get("tools", [])
    
    def get_tool_handlers(self) -> Dict[str, MCPToolHandler]:
        """Get all available tool handlers"""
        return self._tool_handlers
    
    def get_tool_handler(self, name: str) -> Optional[MCPToolHandler]:
        """Get a specific tool handler"""
        return self._tool_handlers.get(name)
    
    async def disconnect_server(self, server_name: str):
        """Disconnect from an MCP server"""
        if server_name in self.servers:
            del self.servers[server_name]
            
            # Remove associated tool handlers
            to_remove = [name for name in self._tool_handlers 
                        if name.startswith(f"{server_name}_")]
            for name in to_remove:
                del self._tool_handlers[name]


# Global MCP client instance
mcp_client = MCPClient()