"""
Simple MCP server example for testing MCP integration

This creates a basic WebSocket server that implements the MCP protocol
with a few example tools.
"""

import asyncio
import json
import websockets
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleMCPServer:
    """Simple MCP server implementation"""
    
    def __init__(self):
        self.tools = {
            "file_read": {
                "name": "file_read",
                "description": "Read the contents of a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        }
                    },
                    "required": ["path"]
                }
            },
            "system_info": {
                "name": "system_info",
                "description": "Get system information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "info_type": {
                            "type": "string",
                            "enum": ["cpu", "memory", "disk", "all"],
                            "description": "Type of system information to retrieve"
                        }
                    },
                    "required": ["info_type"]
                }
            }
        }
    
    async def handle_message(self, websocket, message: str):
        """Handle incoming MCP messages"""
        try:
            data = json.loads(message)
            method = data.get("method")
            params = data.get("params", {})
            msg_id = data.get("id")
            
            if method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "result": {
                        "tools": list(self.tools.values())
                    },
                    "id": msg_id
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name in self.tools:
                    result = await self.execute_tool(tool_name, arguments)
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": msg_id
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,
                            "message": f"Tool '{tool_name}' not found"
                        },
                        "id": msg_id
                    }
            
            else:
                response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found"
                    },
                    "id": msg_id
                }
            
            await websocket.send(json.dumps(response))
            
        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            }
            await websocket.send(json.dumps(error_response))
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": data.get("id") if 'data' in locals() else None
            }
            await websocket.send(json.dumps(error_response))
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Execute a tool and return the result"""
        
        if tool_name == "file_read":
            path = arguments.get("path")
            try:
                with open(path, 'r') as f:
                    content = f.read()
                return {
                    "content": content,
                    "size": len(content),
                    "path": path
                }
            except FileNotFoundError:
                return {"error": f"File not found: {path}"}
            except Exception as e:
                return {"error": str(e)}
        
        elif tool_name == "system_info":
            import platform
            import psutil
            
            info_type = arguments.get("info_type", "all")
            
            result = {}
            
            if info_type in ["cpu", "all"]:
                result["cpu"] = {
                    "count": psutil.cpu_count(),
                    "usage": psutil.cpu_percent(),
                    "architecture": platform.architecture()[0]
                }
            
            if info_type in ["memory", "all"]:
                memory = psutil.virtual_memory()
                result["memory"] = {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percentage": memory.percent
                }
            
            if info_type in ["disk", "all"]:
                disk = psutil.disk_usage('/')
                result["disk"] = {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percentage": (disk.used / disk.total) * 100
                }
            
            if info_type == "all":
                result["platform"] = {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                }
            
            return result
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def handle_client(self, websocket, path):
        """Handle a WebSocket client connection"""
        logger.info(f"Client connected from {websocket.remote_address}")
        
        try:
            async for message in websocket:
                logger.info(f"Received message: {message}")
                await self.handle_message(websocket, message)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Error handling client: {e}")


async def main():
    """Start the MCP server"""
    server = SimpleMCPServer()
    
    print("Starting Simple MCP Server on ws://localhost:8080")
    print("Available tools:")
    for tool_name, tool_def in server.tools.items():
        print(f"  - {tool_name}: {tool_def['description']}")
    
    start_server = websockets.serve(server.handle_client, "localhost", 8080)
    
    await start_server
    
    print("MCP Server is running. Press Ctrl+C to stop.")
    
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("\\nShutting down MCP server...")


if __name__ == "__main__":
    asyncio.run(main())