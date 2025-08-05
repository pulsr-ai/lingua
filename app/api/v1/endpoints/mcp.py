from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.mcp_client import mcp_client, MCPServer
from app.db.base import get_db
from app.db.models import MCPServerModel
from app.schemas.mcp import (
    MCPServerRequest,
    MCPServerResponse,
    MCPToolResponse,
    MCPToolExecuteRequest,
    MCPToolExecuteResponse,
    UpdateMCPServerRequest
)


router = APIRouter()


@router.post("/mcp/servers", response_model=MCPServerResponse)
async def connect_server(request: MCPServerRequest, db: Session = Depends(get_db)):
    """Connect to an MCP server and save to database"""
    try:
        # Save to database first
        db_server = MCPServerModel(
            name=request.name,
            url=request.url,
            protocol=request.protocol,
            api_key=request.api_key,
            connection_status="connecting"
        )
        db.add(db_server)
        db.commit()
        db.refresh(db_server)
        
        # Try to connect
        server = MCPServer(
            name=request.name,
            url=request.url,
            protocol=request.protocol,
            api_key=request.api_key
        )
        
        try:
            await mcp_client.connect_server(server)
            # Update status to connected
            db_server.connection_status = "connected"
            db_server.error_message = None
        except Exception as e:
            # Update status to error
            db_server.connection_status = "error"
            db_server.error_message = str(e)
        
        db.commit()
        db.refresh(db_server)
        
        return db_server
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mcp/servers", response_model=List[MCPServerResponse])
def list_servers(db: Session = Depends(get_db)):
    """List all MCP servers from database"""
    servers = db.query(MCPServerModel).all()
    return servers


@router.delete("/mcp/servers/{server_id}")
async def disconnect_server(server_id: UUID, db: Session = Depends(get_db)):
    """Disconnect from an MCP server and remove from database"""
    server = db.query(MCPServerModel).filter(MCPServerModel.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    try:
        # Disconnect from client
        await mcp_client.disconnect_server(server.name)
        
        # Remove from database
        db.delete(server)
        db.commit()
        
        return {"message": f"Disconnected from MCP server '{server.name}' successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/mcp/servers/{server_id}", response_model=MCPServerResponse)
def update_server(
    server_id: UUID, 
    request: UpdateMCPServerRequest, 
    db: Session = Depends(get_db)
):
    """Update an MCP server configuration"""
    server = db.query(MCPServerModel).filter(MCPServerModel.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    # Update fields
    if request.url is not None:
        server.url = request.url
    if request.protocol is not None:
        server.protocol = request.protocol
    if request.api_key is not None:
        server.api_key = request.api_key
    if request.is_active is not None:
        server.is_active = request.is_active
    
    db.commit()
    db.refresh(server)
    
    return server


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