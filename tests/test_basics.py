import pytest
import json
from httpx import AsyncClient
from app.main import app  # Import your FastAPI app
from app.core.config import settings

BASE_URL = "http://test"

# By default, pytest-asyncio creates a new event loop for each test function.
# To share async fixtures across tests in a module, we need a module-scoped event loop.
@pytest.fixture(scope="module")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(app=app, base_url=BASE_URL) as ac:
        yield ac

@pytest.fixture(scope="module")
async def subtenant(client: AsyncClient):
    """Create a subtenant and return its data."""
    response = await client.post("/api/v1/subtenants/", json={})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    return data

@pytest.fixture(scope="module")
async def registered_functions(client: AsyncClient):
    """Register necessary functions for testing."""
    # Register get_current_time function
    function_code = '''
async def get_current_time(format: str = "%Y-%m-%d %H:%M:%S"):
    """Get the current date and time."""
    from datetime import datetime
    return datetime.now().strftime(format)
'''
    
    response = await client.post("/api/v1/functions/register", json={
        "name": "get_current_time",
        "description": "Get the current date and time",
        "parameters": [
            {
                "name": "format",
                "type": "string",
                "description": "The format string for the date/time (default: %Y-%m-%d %H:%M:%S)",
                "required": False
            }
        ],
        "code": function_code
    })
    
    # If function already exists, that's fine
    if response.status_code not in [200, 400]:
        raise Exception(f"Failed to register function: {response.text}")
    
    return {"get_current_time": "registered"}

@pytest.fixture(scope="module")
async def chat(client: AsyncClient, subtenant: dict, registered_functions: dict):
    """Create a chat for the subtenant and return its data."""
    subtenant_id = subtenant["id"]
    response = await client.post(
        f"/api/v1/subtenants/{subtenant_id}/chats",
        json={"title": "Test Chat"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    return data

@pytest.fixture(scope="module")
async def pirate_chat(client: AsyncClient, subtenant: dict):
    """Create a chat with a pirate system message."""
    subtenant_id = subtenant["id"]
    response = await client.post(
        f"/api/v1/subtenants/{subtenant_id}/chats",
        json={
            "title": "Pirate Chat",
            "system_message": "You are a pirate. All your responses must be in pirate speak."
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    return data

@pytest.mark.asyncio
async def test_create_subtenant(subtenant: dict):
    """Tests if the subtenant fixture created a subtenant successfully."""
    assert "id" in subtenant

@pytest.mark.asyncio
async def test_create_chat(chat: dict):
    """Tests if the chat fixture created a chat successfully."""
    assert "id" in chat

@pytest.mark.asyncio
async def test_send_and_receive_messages(client: AsyncClient, chat: dict):
    """Tests sending a message to a chat and receiving a response."""
    chat_id = chat["id"]
    
    # Send a message asking for the time to ensure tool calling works
    message_data = {"content": "What time is it right now?"}
    response = await client.post(f"/api/v1/chats/{chat_id}/messages", json=message_data)
    assert response.status_code == 200, f"API call failed: {response.text}"
    data = response.json()
    assert data["message"]["role"] == "assistant"
    # The response should contain time-related information
    content = data["message"]["content"].lower()
    # Check for common time-related patterns
    assert any(indicator in content for indicator in [":", "time", "now", "currently", "is"])

    # Verify message history
    response = await client.get(f"/api/v1/chats/{chat_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    # Should have at least: user message, assistant with tool call, tool response, final assistant message
    assert len(messages) >= 3  # Could be 4 if tool call and response are separate
    assert messages[0]["content"] == "What time is it right now?"
    # Check that there was a tool call
    tool_message_found = any(msg["role"] == "tool" for msg in messages)
    assert tool_message_found, "Expected to find a tool response message"

@pytest.mark.asyncio
async def test_pirate_speak(client: AsyncClient, pirate_chat: dict):
    """Tests if the assistant responds in pirate speak."""
    chat_id = pirate_chat["id"]
    
    # Send a message
    message_data = {"content": "Hello, who are you?"}
    response = await client.post(f"/api/v1/chats/{chat_id}/messages", json=message_data)
    assert response.status_code == 200, f"API call failed: {response.text}"
    data = response.json()
    
    # Verify assistant's response is pirate-like
    assert data["message"]["role"] == "assistant"
    # A simple check for common pirate phrases
    assert "Ahoy" in data["message"]["content"] or "matey" in data["message"]["content"]

@pytest.mark.asyncio
async def test_direct_llm_call(client: AsyncClient, subtenant: dict):
    """Tests the direct LLM completion endpoint."""
    # This test assumes the LLM provider is configured and reachable
    subtenant_id = subtenant["id"]
    request_data = {
        "messages": [{"role": "user", "content": "What is the capital of France?"}],
        "model": settings.default_model or "gpt-3.5-turbo"  # Use configured model
    }
    response = await client.post(f"/api/v1/subtenants/{subtenant_id}/llm/complete", json=request_data)
    assert response.status_code == 200, f"API call failed: {response.text}"
    data = response.json()
    assert "Paris" in data["content"]

@pytest.mark.asyncio
async def test_streaming_endpoints(client: AsyncClient, chat: dict, registered_functions: dict):
    """Tests both synchronous and streaming message endpoints."""
    chat_id = chat["id"]
    
    # Test 1: Synchronous endpoint without function calls
    message_data = {"content": "Say hello world"}
    response = await client.post(f"/api/v1/chats/{chat_id}/messages", json=message_data)
    assert response.status_code == 200
    data = response.json()
    assert data["message"]["role"] == "assistant"
    assert "hello" in data["message"]["content"].lower() or "world" in data["message"]["content"].lower()
    
    # Test 2: Streaming endpoint without function calls
    message_data = {"content": "Say goodbye world"}
    
    # Use httpx streaming
    async with client.stream(
        "POST", 
        f"/api/v1/chats/{chat_id}/messages/stream",
        json=message_data
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Collect all chunks
        chunks = []
        async for chunk in response.aiter_text():
            if chunk.strip():  # Skip empty chunks
                chunks.append(chunk.strip())
        
        # Verify we got some data chunks
        assert len(chunks) > 0, "Expected to receive streamed chunks"
        
        # Join all chunks and split by lines to handle SSE format
        full_response = "\n".join(chunks)
        lines = [line.strip() for line in full_response.split('\n') if line.strip()]
        
        # Find data lines
        data_chunks = [line for line in lines if line.startswith("data: ")]
        assert len(data_chunks) > 0, f"Expected data chunks, got lines: {lines}"
        
        # Check for [DONE] signal
        done_found = any("[DONE]" in chunk for chunk in data_chunks)
        assert done_found, "Expected [DONE] signal in stream"
        
        # Parse actual content chunks (excluding [DONE])
        content_chunks = []
        for chunk in data_chunks:
            if "[DONE]" not in chunk:
                try:
                    # Parse JSON after "data: "
                    json_str = chunk[6:]  # Remove "data: " prefix
                    data = json.loads(json_str)
                    if "content" in data and data["content"]:
                        content_chunks.append(data["content"])
                except json.JSONDecodeError:
                    continue
        
        # Verify we got some content for basic streaming
        assert len(content_chunks) > 0, f"Expected content chunks, got data chunks: {data_chunks}"
        
        # Combine all content chunks
        full_content = "".join(content_chunks).lower()
        
        # The response should contain goodbye or world
        assert any(word in full_content for word in ["goodbye", "bye", "world"]), \
            f"Expected 'goodbye' or 'world' in content, got: {full_content}"
    
    # Test 3: Synchronous endpoint with function calls
    message_data = {"content": "What time is it right now?"}
    response = await client.post(f"/api/v1/chats/{chat_id}/messages", json=message_data)
    assert response.status_code == 200
    data = response.json()
    assert data["message"]["role"] == "assistant"
    # The response should contain time-related information
    content = data["message"]["content"].lower()
    assert any(indicator in content for indicator in [":", "time", "now", "currently", "is"])
    
    # Test 4: Streaming endpoint with function calls
    message_data = {"content": "What's the current time in ISO format?"}
    
    # Use httpx streaming for function call
    async with client.stream(
        "POST", 
        f"/api/v1/chats/{chat_id}/messages/stream",
        json=message_data
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Collect all chunks
        chunks = []
        async for chunk in response.aiter_text():
            if chunk.strip():  # Skip empty chunks
                chunks.append(chunk.strip())
        
        # Verify we got some data chunks
        assert len(chunks) > 0, "Expected to receive streamed chunks for function call"
        
        # Join all chunks and split by lines to handle SSE format
        full_response = "\n".join(chunks)
        lines = [line.strip() for line in full_response.split('\n') if line.strip()]
        
        # Find data lines
        data_chunks = [line for line in lines if line.startswith("data: ")]
        assert len(data_chunks) > 0, f"Expected data chunks for function call, got lines: {lines}"
        
        # Check for [DONE] signal
        done_found = any("[DONE]" in chunk for chunk in data_chunks)
        assert done_found, "Expected [DONE] signal in function call stream"
        
        # Parse actual content chunks (excluding [DONE])
        content_chunks = []
        for chunk in data_chunks:
            if "[DONE]" not in chunk:
                try:
                    # Parse JSON after "data: "
                    json_str = chunk[6:]  # Remove "data: " prefix
                    data = json.loads(json_str)
                    if "content" in data and data["content"]:
                        content_chunks.append(data["content"])
                except json.JSONDecodeError:
                    continue
        
        # Check if we got the tool execution separator
        tool_execution_found = any("[Tool execution completed]" in chunk for chunk in content_chunks)
        
        # Combine all content chunks
        full_content = "".join(content_chunks)
        
        # If tool execution was found, we should have time information after it
        if tool_execution_found:
            # Split by the tool execution marker
            parts = full_content.split("[Tool execution completed]")
            if len(parts) > 1:
                final_response = parts[1].strip().lower()
                # Should contain time-related information
                assert any(indicator in final_response for indicator in [":", "time", "iso", "format"]), \
                    f"Expected time information in final response, got: {final_response}"
        else:
            # Even without the separator, we should have some time-related content
            assert any(indicator in full_content.lower() for indicator in ["time", ":", "current"]), \
                f"Expected time-related content, got: {full_content}"
    
    # Test 5: Verify message history contains all interactions
    response = await client.get(f"/api/v1/chats/{chat_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    
    # Should have messages from all 4 tests above
    # Each test adds at least 2 messages (user + assistant)
    assert len(messages) >= 8, f"Expected at least 8 messages, got {len(messages)}: {[m['role'] for m in messages]}"
    
    # Verify we have tool messages from the time requests
    tool_messages = [m for m in messages if m["role"] == "tool"]
    # At least one tool message should exist from the time requests
    assert len(tool_messages) >= 1, f"Expected at least 1 tool message from time requests, got {len(tool_messages)}"
    
    # Verify the time requests resulted in proper responses
    time_requests = [m for m in messages if "time" in m.get("content", "").lower() and m["role"] == "user"]
    assert len(time_requests) >= 2, f"Expected at least 2 time-related user messages, got {len(time_requests)}"
    
    # Test 6: Test with provider_name in request body
    message_data = {
        "content": "Count from 1 to 3",
        "provider_name": None  # Use default provider
    }
    response = await client.post(f"/api/v1/chats/{chat_id}/messages", json=message_data)
    assert response.status_code == 200
    data = response.json()
    assert data["message"]["role"] == "assistant"
    # Should contain numbers 1, 2, 3
    content = data["message"]["content"]
    assert "1" in content and "2" in content and "3" in content 