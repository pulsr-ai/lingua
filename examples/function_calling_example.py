"""
Example demonstrating function calling capabilities of the LLM wrapper service

This example shows:
1. How to create custom functions
2. How to register functions
3. How to use functions in chat messages
4. How to connect to MCP servers
"""

import asyncio
import httpx
import json
from typing import Dict, Any


async def example_function_calling():
    """Example of using function calling with the LLM service"""
    
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        # 1. Create a subtenant
        print("Creating subtenant...")
        subtenant_response = await client.post(f"{base_url}/subtenants", json={})
        subtenant = subtenant_response.json()
        subtenant_id = subtenant["id"]
        print(f"Created subtenant: {subtenant_id}")
        
        # 2. Create a chat
        print("Creating chat...")
        chat_response = await client.post(
            f"{base_url}/subtenants/{subtenant_id}/chats",
            json={"title": "Function Calling Demo"}
        )
        chat = chat_response.json()
        chat_id = chat["id"]
        print(f"Created chat: {chat_id}")
        
        # 3. List available functions
        print("\\nAvailable functions:")
        functions_response = await client.get(f"{base_url}/functions")
        functions = functions_response.json()
        for func in functions:
            print(f"- {func['name']}: {func['description']}")
        
        # 4. Send a message that should trigger function calling
        print("\\nSending message that requires function calling...")
        message_request = {
            "content": "What time is it right now? Also, can you calculate 15 * 23?",
            "include_memories": False,
            "stream": False
        }
        
        message_response = await client.post(
            f"{base_url}/chats/{chat_id}/messages",
            json=message_request
        )
        
        if message_response.status_code == 200:
            response = message_response.json()
            print(f"Assistant response: {response['message']['content']}")
        else:
            print(f"Error: {message_response.status_code} - {message_response.text}")
        
        # 5. Register a custom function
        print("\\nRegistering a custom function...")
        custom_function = {
            "name": "weather_check",
            "description": "Get the current weather for a location",
            "parameters": [
                {
                    "name": "location",
                    "type": "string",
                    "description": "The location to check weather for",
                    "required": True
                }
            ],
            "code": '''
def weather_function(location):
    # This is a mock weather function
    import random
    temperatures = [20, 25, 18, 30, 15, 22]
    conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]
    
    return {
        "location": location,
        "temperature": random.choice(temperatures),
        "condition": random.choice(conditions),
        "humidity": random.randint(30, 80)
    }
'''
        }
        
        register_response = await client.post(f"{base_url}/functions/register", json=custom_function)
        if register_response.status_code == 200:
            print("Custom function registered successfully!")
            
            # Test the custom function
            print("\\nTesting weather function...")
            weather_request = {
                "content": "What's the weather like in New York?",
                "include_memories": False,
                "stream": False
            }
            
            weather_response = await client.post(
                f"{base_url}/chats/{chat_id}/messages",
                json=weather_request
            )
            
            if weather_response.status_code == 200:
                response = weather_response.json()
                print(f"Weather response: {response['message']['content']}")
        
        # 6. Connect to an MCP server (example)
        print("\\nExample MCP server connection (this will fail without a real server):")
        mcp_server = {
            "name": "example_server",
            "url": "ws://localhost:8080/mcp",
            "protocol": "websocket"
        }
        
        try:
            mcp_response = await client.post(f"{base_url}/mcp/servers", json=mcp_server)
            if mcp_response.status_code == 200:
                print("MCP server connected successfully!")
                
                # List MCP tools
                tools_response = await client.get(f"{base_url}/mcp/tools")
                tools = tools_response.json()
                print("Available MCP tools:")
                for tool in tools:
                    print(f"- {tool['name']}: {tool['description']}")
            else:
                print(f"MCP connection failed: {mcp_response.text}")
        except Exception as e:
            print(f"MCP connection failed (expected): {e}")


async def example_direct_function_execution():
    """Example of directly executing functions"""
    
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        # Execute the calculator function directly
        print("Executing calculator function directly...")
        calc_request = {
            "arguments": {"expression": "2 + 2 * 3"}
        }
        
        calc_response = await client.post(f"{base_url}/functions/calculator/execute", json=calc_request)
        if calc_response.status_code == 200:
            result = calc_response.json()
            print(f"Calculator result: {result['result']}")
        
        # Execute the time function
        print("\\nExecuting time function directly...")
        time_request = {
            "arguments": {"format": "%Y-%m-%d %H:%M:%S"}
        }
        
        time_response = await client.post(f"{base_url}/functions/get_current_time/execute", json=time_request)
        if time_response.status_code == 200:
            result = time_response.json()
            print(f"Current time: {result['result']}")


if __name__ == "__main__":
    print("Function Calling Example")
    print("=======================")
    print("Make sure the LLM service is running on http://localhost:8000")
    print("And you have an OpenAI API key configured")
    print()
    
    # Run the examples
    asyncio.run(example_function_calling())
    print("\\n" + "="*50)
    asyncio.run(example_direct_function_execution())