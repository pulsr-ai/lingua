from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.functions import function_registry
from app.core.mcp_client import mcp_client


class AvailableToolsResponse(BaseModel):
    functions: List[Dict[str, Any]]
    mcp_tools: List[Dict[str, Any]]


router = APIRouter()


@router.get("/tools/available", response_model=AvailableToolsResponse)
def list_available_tools():
    """List all available functions and MCP tools"""
    
    # Get all function definitions
    function_tools = function_registry.get_definitions()
    functions = []
    for tool in function_tools:
        functions.append({
            "name": tool["function"]["name"],
            "description": tool["function"]["description"],
            "parameters": tool["function"]["parameters"]
        })
    
    # Get all MCP tool definitions
    mcp_tool_defs = mcp_client.get_tools_definitions()
    mcp_tools = []
    for tool in mcp_tool_defs:
        mcp_tools.append({
            "name": tool["function"]["name"],
            "description": tool["function"]["description"],
            "parameters": tool["function"]["parameters"]
        })
    
    return AvailableToolsResponse(
        functions=functions,
        mcp_tools=mcp_tools
    )


@router.get("/tools/names")
def list_tool_names():
    """List just the names of available tools for easy reference"""
    
    # Get function names
    function_tools = function_registry.get_definitions()
    function_names = [tool["function"]["name"] for tool in function_tools]
    
    # Get MCP tool names
    mcp_tool_defs = mcp_client.get_tools_definitions()
    mcp_tool_names = [tool["function"]["name"] for tool in mcp_tool_defs]
    
    return {
        "functions": function_names,
        "mcp_tools": mcp_tool_names
    }