from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from app.core.mcp_client import mcp_client, MCPServer
from app.schemas.mcp import (
    MCPServerRequest,
    MCPServerResponse,
    MCPToolResponse,
    MCPToolExecuteRequest,
    MCPToolExecuteResponse
)


router = APIRouter()


@router.post("/mcp/servers")
async def connect_server(request: MCPServerRequest):
    """Connect to an MCP server"""
    try:
        server = MCPServer(
            name=request.name,
            url=request.url,
            protocol=request.protocol,
            api_key=request.api_key
        )
        
        await mcp_client.connect_server(server)
        return {"message": f"Connected to MCP server '{request.name}' successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mcp/servers", response_model=List[MCPServerResponse])
def list_servers():
    """List all connected MCP servers"""
    servers = []
    for name, server in mcp_client.servers.items():
        servers.append(MCPServerResponse(
            name=server.name,
            url=server.url,
            protocol=server.protocol,
            connected=True
        ))
    return servers


@router.delete("/mcp/servers/{server_name}")
async def disconnect_server(server_name: str):
    """Disconnect from an MCP server"""
    try:
        await mcp_client.disconnect_server(server_name)
        return {"message": f"Disconnected from MCP server '{server_name}' successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mcp/tools", response_model=List[MCPToolResponse])
def list_tools():
    """List all available MCP tools"""
    tools = []
    for name, handler in mcp_client.get_tool_handlers().items():
        definition = handler.get_definition()
        server_name = name.split('_')[0]  # Extract server name from tool name
        
        # Convert parameters to dict format
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in definition.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            
            parameters["properties"][param.name] = prop
            if param.required:
                parameters["required"].append(param.name)
        
        tools.append(MCPToolResponse(
            name=name,
            description=definition.description,
            server=server_name,
            parameters=parameters
        ))
    
    return tools


@router.post("/mcp/tools/{tool_name}/execute", response_model=MCPToolExecuteResponse)
async def execute_tool(tool_name: str, request: MCPToolExecuteRequest):
    """Execute an MCP tool"""
    try:
        handler = mcp_client.get_tool_handler(tool_name)
        if not handler:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        result = await handler.execute(**request.arguments)
        return MCPToolExecuteResponse(result=result)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))