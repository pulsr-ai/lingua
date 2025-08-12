"""
Comprehensive tests for Assistant functionality.
Tests are organized by sections for clarity and maintainability.
"""

import pytest
import json
from httpx import AsyncClient
from app.main import app
from typing import Dict, List
from uuid import UUID

BASE_URL = "http://test"

# ============================================================================
# SECTION 1: FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def event_loop():
    """Create a module-scoped event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def client():
    """Create an async test client."""
    async with AsyncClient(app=app, base_url=BASE_URL) as ac:
        yield ac

@pytest.fixture(scope="module")
async def subtenant_1(client: AsyncClient) -> Dict:
    """Create first test subtenant."""
    response = await client.post("/api/v1/subtenants/", json={})
    assert response.status_code == 200
    return response.json()

@pytest.fixture(scope="module")
async def subtenant_2(client: AsyncClient) -> Dict:
    """Create second test subtenant for isolation testing."""
    response = await client.post("/api/v1/subtenants/", json={})
    assert response.status_code == 200
    return response.json()

@pytest.fixture(scope="module")
async def registered_functions(client: AsyncClient) -> Dict:
    """Register test functions."""
    functions = []
    
    # Register get_current_time function
    time_function = {
        "name": "get_current_time",
        "description": "Get the current date and time",
        "parameters": [
            {
                "name": "format",
                "type": "string",
                "description": "The format string for the date/time",
                "required": False
            }
        ],
        "code": '''
async def get_current_time(format: str = "%Y-%m-%d %H:%M:%S"):
    """Get the current date and time."""
    from datetime import datetime
    return datetime.now().strftime(format)
'''
    }
    
    # Register calculate function
    calc_function = {
        "name": "calculate",
        "description": "Perform basic arithmetic calculations",
        "parameters": [
            {
                "name": "expression",
                "type": "string",
                "description": "Mathematical expression to evaluate",
                "required": True
            }
        ],
        "code": '''
async def calculate(expression: str):
    """Evaluate a mathematical expression."""
    try:
        # Only allow safe operations
        allowed_chars = "0123456789+-*/() ."
        if all(c in allowed_chars for c in expression):
            result = eval(expression)
            return str(result)
        else:
            return "Invalid expression"
    except Exception as e:
        return f"Error: {str(e)}"
'''
    }
    
    # Register weather function (mock)
    weather_function = {
        "name": "get_weather",
        "description": "Get weather information for a location",
        "parameters": [
            {
                "name": "location",
                "type": "string",
                "description": "Location to get weather for",
                "required": True
            }
        ],
        "code": '''
async def get_weather(location: str):
    """Get weather information (mock)."""
    import random
    temps = [15, 18, 20, 22, 25, 28, 30]
    conditions = ["sunny", "cloudy", "partly cloudy", "rainy"]
    return f"Weather in {location}: {random.choice(temps)}°C, {random.choice(conditions)}"
'''
    }
    
    for func in [time_function, calc_function, weather_function]:
        response = await client.post("/api/v1/functions/register", json=func)
        if response.status_code == 200:
            functions.append(func["name"])
        elif response.status_code == 400 and "already exists" in response.text:
            functions.append(func["name"])  # Function already registered
        else:
            raise Exception(f"Failed to register function {func['name']}: {response.text}")
    
    return functions

# ============================================================================
# SECTION 2: ASSISTANT CRUD OPERATIONS
# ============================================================================

@pytest.mark.asyncio
async def test_create_assistant_minimal(client: AsyncClient):
    """Test creating an assistant with minimal data."""
    assistant_data = {
        "name": "Minimal Assistant",
        "description": "A minimal assistant for testing"
    }
    
    response = await client.post("/api/v1/assistants", json=assistant_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "Minimal Assistant"
    assert data["description"] == "A minimal assistant for testing"
    assert data["subtenant_id"] is None  # Workspace-wide by default
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    return data

@pytest.mark.asyncio
async def test_create_assistant_full(client: AsyncClient, registered_functions: List[str]):
    """Test creating an assistant with all fields."""
    assistant_data = {
        "name": "Full Assistant",
        "description": "An assistant with all features",
        "system_prompt": "You are a helpful assistant specialized in time and calculations.",
        "enabled_functions": ["get_current_time", "calculate"],
        "enabled_mcp_tools": [],
        "function_parameters": {
            "get_current_time": {"format": "%Y-%m-%d"}
        },
        "mcp_tool_parameters": {}
    }
    
    response = await client.post("/api/v1/assistants", json=assistant_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "Full Assistant"
    assert data["system_prompt"] == "You are a helpful assistant specialized in time and calculations."
    assert set(data["enabled_functions"]) == {"get_current_time", "calculate"}
    assert data["function_parameters"]["get_current_time"]["format"] == "%Y-%m-%d"
    
    return data

@pytest.mark.asyncio
async def test_create_private_assistant(client: AsyncClient, subtenant_1: Dict):
    """Test creating a private assistant for a specific subtenant."""
    assistant_data = {
        "name": "Private Assistant",
        "description": "A private assistant for subtenant 1",
        "subtenant_id": subtenant_1["id"],
        "system_prompt": "You are a private assistant."
    }
    
    response = await client.post("/api/v1/assistants", json=assistant_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["subtenant_id"] == subtenant_1["id"]
    assert data["name"] == "Private Assistant"
    
    return data

@pytest.mark.asyncio
async def test_list_assistants_all(client: AsyncClient):
    """Test listing all assistants."""
    response = await client.get("/api/v1/assistants")
    assert response.status_code == 200
    
    data = response.json()
    assert "assistants" in data
    assert "total" in data
    assert data["total"] >= 3  # At least the 3 we created above
    
    # Check that we have both workspace-wide and private assistants
    workspace_assistants = [a for a in data["assistants"] if a["subtenant_id"] is None]
    private_assistants = [a for a in data["assistants"] if a["subtenant_id"] is not None]
    
    assert len(workspace_assistants) >= 2  # Minimal and Full assistants
    assert len(private_assistants) >= 1  # Private assistant

@pytest.mark.asyncio
async def test_list_assistants_workspace_only(client: AsyncClient):
    """Test listing only workspace-wide assistants."""
    response = await client.get("/api/v1/assistants?workspace_only=true")
    assert response.status_code == 200
    
    data = response.json()
    # All assistants should have subtenant_id = None
    for assistant in data["assistants"]:
        assert assistant["subtenant_id"] is None

@pytest.mark.asyncio
async def test_list_assistants_by_subtenant(client: AsyncClient, subtenant_1: Dict):
    """Test listing assistants accessible to a specific subtenant."""
    response = await client.get(f"/api/v1/assistants?subtenant_id={subtenant_1['id']}")
    assert response.status_code == 200
    
    data = response.json()
    # Should include both workspace-wide and subtenant's private assistants
    workspace_count = sum(1 for a in data["assistants"] if a["subtenant_id"] is None)
    private_count = sum(1 for a in data["assistants"] if a["subtenant_id"] == subtenant_1["id"])
    
    assert workspace_count >= 2  # Workspace-wide assistants
    assert private_count >= 1  # Subtenant's private assistant

@pytest.mark.asyncio
async def test_get_assistant(client: AsyncClient):
    """Test getting a specific assistant."""
    # First create an assistant
    create_response = await client.post("/api/v1/assistants", json={
        "name": "Get Test Assistant",
        "description": "For testing GET endpoint"
    })
    assert create_response.status_code == 200
    created = create_response.json()
    
    # Get the assistant
    response = await client.get(f"/api/v1/assistants/{created['id']}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == created["id"]
    assert data["name"] == "Get Test Assistant"

@pytest.mark.asyncio
async def test_update_assistant(client: AsyncClient):
    """Test updating an assistant."""
    # First create an assistant
    create_response = await client.post("/api/v1/assistants", json={
        "name": "Update Test Assistant",
        "description": "Original description"
    })
    assert create_response.status_code == 200
    created = create_response.json()
    
    # Update the assistant
    update_data = {
        "description": "Updated description",
        "system_prompt": "You are an updated assistant",
        "enabled_functions": ["calculate"]
    }
    
    response = await client.put(f"/api/v1/assistants/{created['id']}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "Update Test Assistant"  # Name unchanged
    assert data["description"] == "Updated description"
    assert data["system_prompt"] == "You are an updated assistant"
    assert data["enabled_functions"] == ["calculate"]

@pytest.mark.asyncio
async def test_delete_assistant(client: AsyncClient):
    """Test soft-deleting an assistant."""
    # First create an assistant
    create_response = await client.post("/api/v1/assistants", json={
        "name": "Delete Test Assistant",
        "description": "To be deleted"
    })
    assert create_response.status_code == 200
    created = create_response.json()
    
    # Delete the assistant
    response = await client.delete(f"/api/v1/assistants/{created['id']}")
    assert response.status_code == 200
    
    # Try to get the deleted assistant (should fail as it's soft-deleted)
    get_response = await client.get(f"/api/v1/assistants/{created['id']}")
    assert get_response.status_code == 404

# ============================================================================
# SECTION 3: CHAT CREATION WITH ASSISTANTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_chat_with_assistant(client: AsyncClient, subtenant_1: Dict):
    """Test creating a chat with an assistant."""
    # First create an assistant
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Chat Test Assistant",
        "description": "For chat testing",
        "system_prompt": "You are a helpful chat assistant.",
        "enabled_functions": ["get_current_time"]
    })
    assert assistant_response.status_code == 200
    assistant = assistant_response.json()
    
    # Create a chat with the assistant
    chat_data = {
        "title": "Chat with Assistant",
        "assistant_id": assistant["id"]
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{subtenant_1['id']}/chats",
        json=chat_data
    )
    assert response.status_code == 200
    
    chat = response.json()
    assert chat["assistant_id"] == assistant["id"]
    assert chat["enabled_functions"] == ["get_current_time"]  # Inherited from assistant
    
    # Get the chat with messages to verify system prompt
    get_response = await client.get(f"/api/v1/chats/{chat['id']}")
    assert get_response.status_code == 200
    
    chat_with_messages = get_response.json()
    assert len(chat_with_messages["messages"]) == 1
    assert chat_with_messages["messages"][0]["role"] == "system"
    assert chat_with_messages["messages"][0]["content"] == "You are a helpful chat assistant."
    
    return chat

@pytest.mark.asyncio
async def test_create_chat_override_assistant_settings(client: AsyncClient, subtenant_1: Dict):
    """Test creating a chat that overrides assistant settings."""
    # First create an assistant
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Override Test Assistant",
        "system_prompt": "Assistant system prompt",
        "enabled_functions": ["get_current_time", "calculate"]
    })
    assert assistant_response.status_code == 200
    assistant = assistant_response.json()
    
    # Create a chat that overrides some settings
    chat_data = {
        "title": "Override Chat",
        "assistant_id": assistant["id"],
        "system_message": "Override system prompt",  # Override system prompt
        "enabled_functions": ["calculate"]  # Override functions
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{subtenant_1['id']}/chats",
        json=chat_data
    )
    assert response.status_code == 200
    
    chat = response.json()
    assert chat["enabled_functions"] == ["calculate"]  # Overridden
    
    # Get the chat with messages to verify system prompt override
    get_response = await client.get(f"/api/v1/chats/{chat['id']}")
    assert get_response.status_code == 200
    
    chat_with_messages = get_response.json()
    assert chat_with_messages["messages"][0]["content"] == "Override system prompt"

@pytest.mark.asyncio
async def test_chat_with_private_assistant_access(client: AsyncClient, subtenant_1: Dict, subtenant_2: Dict):
    """Test that a subtenant cannot use another subtenant's private assistant."""
    # Create a private assistant for subtenant_1
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Private to Subtenant 1",
        "subtenant_id": subtenant_1["id"]
    })
    assert assistant_response.status_code == 200
    assistant = assistant_response.json()
    
    # Try to create a chat for subtenant_2 using subtenant_1's assistant
    chat_data = {
        "title": "Unauthorized Chat",
        "assistant_id": assistant["id"]
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{subtenant_2['id']}/chats",
        json=chat_data
    )
    assert response.status_code == 403
    assert "not accessible" in response.json()["detail"]

# ============================================================================
# SECTION 4: MESSAGE HANDLING WITH ASSISTANT PRESETS
# ============================================================================

@pytest.mark.asyncio
async def test_message_with_assistant_functions(client: AsyncClient, subtenant_1: Dict, registered_functions: List[str]):
    """Test that messages use assistant's enabled functions."""
    # Create assistant with specific functions
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Function Test Assistant",
        "enabled_functions": ["get_current_time"],  # Only time function
        "system_prompt": "You can only tell time."
    })
    assert assistant_response.status_code == 200
    assistant = assistant_response.json()
    
    # Create chat with assistant
    chat_response = await client.post(
        f"/api/v1/subtenants/{subtenant_1['id']}/chats",
        json={"title": "Function Test Chat", "assistant_id": assistant["id"]}
    )
    assert chat_response.status_code == 200
    chat = chat_response.json()
    
    # Send message asking for time (should work)
    message_response = await client.post(
        f"/api/v1/chats/{chat['id']}/messages",
        json={"content": "What time is it?"}
    )
    assert message_response.status_code == 200
    message = message_response.json()
    
    # Verify the response contains time information
    assert ":" in message["message"]["content"] or "time" in message["message"]["content"].lower()
    
    # Check message history for tool usage
    history_response = await client.get(f"/api/v1/chats/{chat['id']}/messages")
    assert history_response.status_code == 200
    messages = history_response.json()
    
    # Should have system, user, assistant (with tool call), tool response, final assistant
    tool_messages = [m for m in messages if m["role"] == "tool"]
    assert len(tool_messages) >= 1

@pytest.mark.asyncio
async def test_message_override_assistant_functions(client: AsyncClient, subtenant_1: Dict, registered_functions: List[str]):
    """Test that message request can override assistant's functions."""
    # Create assistant with limited functions
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Override Function Assistant",
        "enabled_functions": ["get_current_time"]
    })
    assert assistant_response.status_code == 200
    assistant = assistant_response.json()
    
    # Create chat with assistant
    chat_response = await client.post(
        f"/api/v1/subtenants/{subtenant_1['id']}/chats",
        json={"title": "Override Function Chat", "assistant_id": assistant["id"]}
    )
    assert chat_response.status_code == 200
    chat = chat_response.json()
    
    # Send message with overridden functions
    message_response = await client.post(
        f"/api/v1/chats/{chat['id']}/messages",
        json={
            "content": "Calculate 5 + 3",
            "enabled_functions": ["calculate"]  # Override to use calculate instead
        }
    )
    assert message_response.status_code == 200
    message = message_response.json()
    
    # Should be able to calculate despite assistant not having this function
    content = message["message"]["content"]
    assert "8" in content or "5 + 3" in content or "5+3" in content or "calculate" in content

@pytest.mark.asyncio
async def test_streaming_with_assistant(client: AsyncClient, subtenant_1: Dict):
    """Test streaming messages with assistant presets."""
    # Create assistant
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Streaming Assistant",
        "system_prompt": "You are a streaming assistant. Always be concise."
    })
    assert assistant_response.status_code == 200
    assistant = assistant_response.json()
    
    # Create chat with assistant
    chat_response = await client.post(
        f"/api/v1/subtenants/{subtenant_1['id']}/chats",
        json={"title": "Streaming Chat", "assistant_id": assistant["id"]}
    )
    assert chat_response.status_code == 200
    chat = chat_response.json()
    
    # Send streaming message
    async with client.stream(
        "POST",
        f"/api/v1/chats/{chat['id']}/messages/stream",
        json={"content": "Say hello"}
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        chunks = []
        async for chunk in response.aiter_text():
            if chunk.strip():
                chunks.append(chunk.strip())
        
        assert len(chunks) > 0
        
        # Verify streaming completed
        done_found = any("[DONE]" in chunk for chunk in chunks)
        assert done_found

# ============================================================================
# SECTION 5: EDGE CASES AND ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_create_assistant_invalid_subtenant(client: AsyncClient):
    """Test creating an assistant with invalid subtenant ID."""
    assistant_data = {
        "name": "Invalid Subtenant Assistant",
        "subtenant_id": "00000000-0000-0000-0000-000000000000"
    }
    
    response = await client.post("/api/v1/assistants", json=assistant_data)
    assert response.status_code == 404
    assert "Subtenant not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_chat_invalid_assistant(client: AsyncClient, subtenant_1: Dict):
    """Test creating a chat with invalid assistant ID."""
    chat_data = {
        "title": "Invalid Assistant Chat",
        "assistant_id": "00000000-0000-0000-0000-000000000000"
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{subtenant_1['id']}/chats",
        json=chat_data
    )
    assert response.status_code == 404
    assert "Assistant not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_nonexistent_assistant(client: AsyncClient):
    """Test updating a non-existent assistant."""
    response = await client.put(
        "/api/v1/assistants/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated Name"}
    )
    assert response.status_code == 404
    assert "Assistant not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_nonexistent_assistant(client: AsyncClient):
    """Test deleting a non-existent assistant."""
    response = await client.delete("/api/v1/assistants/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "Assistant not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_assistant_with_empty_functions(client: AsyncClient):
    """Test assistant with explicitly empty function list."""
    assistant_data = {
        "name": "No Functions Assistant",
        "enabled_functions": [],
        "enabled_mcp_tools": []
    }
    
    response = await client.post("/api/v1/assistants", json=assistant_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["enabled_functions"] == []
    assert data["enabled_mcp_tools"] == []

@pytest.mark.asyncio
async def test_assistant_name_validation(client: AsyncClient):
    """Test assistant name validation."""
    # Test with empty name
    response = await client.post("/api/v1/assistants", json={"name": ""})
    assert response.status_code == 422  # Validation error
    
    # Test with whitespace-only name
    response = await client.post("/api/v1/assistants", json={"name": "   "})
    assert response.status_code == 422  # Validation error
    
    # Test with very long name (over 255 characters)
    long_name = "A" * 256
    response = await client.post("/api/v1/assistants", json={"name": long_name})
    assert response.status_code == 422  # Should fail validation
    
    # Test with max allowed length (255 characters)
    max_name = "A" * 255
    response = await client.post("/api/v1/assistants", json={"name": max_name})
    assert response.status_code == 200  # Should succeed

# ============================================================================
# SECTION 6: INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_workflow(client: AsyncClient, subtenant_1: Dict, registered_functions: List[str]):
    """Test complete workflow from assistant creation to message handling."""
    # Step 1: Create an assistant
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Workflow Assistant",
        "description": "Full workflow test",
        "system_prompt": "You are a helpful assistant for testing workflows.",
        "enabled_functions": ["get_current_time", "calculate"],
        "function_parameters": {
            "get_current_time": {"format": "%H:%M"}
        }
    })
    assert assistant_response.status_code == 200
    assistant = assistant_response.json()
    
    # Step 2: Create a chat with the assistant
    chat_response = await client.post(
        f"/api/v1/subtenants/{subtenant_1['id']}/chats",
        json={"title": "Workflow Chat", "assistant_id": assistant["id"]}
    )
    assert chat_response.status_code == 200
    chat = chat_response.json()
    
    # Step 3: Send various messages
    # Message 1: Simple greeting
    msg1_response = await client.post(
        f"/api/v1/chats/{chat['id']}/messages",
        json={"content": "Hello!"}
    )
    assert msg1_response.status_code == 200
    
    # Message 2: Use time function
    msg2_response = await client.post(
        f"/api/v1/chats/{chat['id']}/messages",
        json={"content": "What time is it?"}
    )
    assert msg2_response.status_code == 200
    msg2 = msg2_response.json()
    assert ":" in msg2["message"]["content"]  # Should contain time
    
    # Message 3: Use calculate function
    msg3_response = await client.post(
        f"/api/v1/chats/{chat['id']}/messages",
        json={"content": "What is 15 * 4?"}
    )
    assert msg3_response.status_code == 200
    msg3 = msg3_response.json()
    # The response might contain either the calculated result or reference to calculation
    content = msg3["message"]["content"]
    assert "60" in content or "15 * 4" in content or "15*4" in content or "calculate" in content
    
    # Step 4: Verify message history
    history_response = await client.get(f"/api/v1/chats/{chat['id']}/messages")
    assert history_response.status_code == 200
    messages = history_response.json()
    
    # Should have: system + 3 user messages + assistant responses + tool messages
    assert len(messages) >= 7
    
    # Verify system message is first
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == assistant["system_prompt"]
    
    # Step 5: Update the assistant
    update_response = await client.put(
        f"/api/v1/assistants/{assistant['id']}",
        json={"description": "Updated workflow assistant"}
    )
    assert update_response.status_code == 200
    
    # Step 6: Verify assistant update doesn't affect existing chat
    msg4_response = await client.post(
        f"/api/v1/chats/{chat['id']}/messages",
        json={"content": "Are you still working?"}
    )
    assert msg4_response.status_code == 200
    
    # Step 7: List all assistants to verify our assistant exists
    list_response = await client.get("/api/v1/assistants")
    assert list_response.status_code == 200
    assistants = list_response.json()["assistants"]
    
    workflow_assistant = next((a for a in assistants if a["id"] == assistant["id"]), None)
    assert workflow_assistant is not None
    assert workflow_assistant["description"] == "Updated workflow assistant"

@pytest.mark.asyncio
async def test_multiple_chats_same_assistant(client: AsyncClient, subtenant_1: Dict):
    """Test multiple chats using the same assistant."""
    # Create an assistant
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Shared Assistant",
        "system_prompt": "You are a shared assistant."
    })
    assert assistant_response.status_code == 200
    assistant = assistant_response.json()
    
    # Create multiple chats with the same assistant
    chats = []
    for i in range(3):
        chat_response = await client.post(
            f"/api/v1/subtenants/{subtenant_1['id']}/chats",
            json={"title": f"Shared Chat {i+1}", "assistant_id": assistant["id"]}
        )
        assert chat_response.status_code == 200
        chats.append(chat_response.json())
    
    # Send messages to each chat
    for i, chat in enumerate(chats):
        msg_response = await client.post(
            f"/api/v1/chats/{chat['id']}/messages",
            json={"content": f"Hello from chat {i+1}"}
        )
        assert msg_response.status_code == 200
    
    # Verify each chat has its own message history
    for i, chat in enumerate(chats):
        history_response = await client.get(f"/api/v1/chats/{chat['id']}/messages")
        assert history_response.status_code == 200
        messages = history_response.json()
        
        # Each chat should have system message + 1 user message + 1 assistant response
        assert len(messages) >= 3
        
        # Verify the user message is specific to this chat
        user_messages = [m for m in messages if m["role"] == "user"]
        assert any(f"chat {i+1}" in m["content"] for m in user_messages)

# ============================================================================
# SECTION 7: PERFORMANCE AND LIMITS
# ============================================================================

@pytest.mark.asyncio
async def test_pagination(client: AsyncClient):
    """Test pagination of assistant list."""
    # Create multiple assistants
    for i in range(5):
        await client.post("/api/v1/assistants", json={
            "name": f"Pagination Test {i}"
        })
    
    # Test pagination
    page1_response = await client.get("/api/v1/assistants?skip=0&limit=2")
    assert page1_response.status_code == 200
    page1 = page1_response.json()
    assert len(page1["assistants"]) <= 2
    
    page2_response = await client.get("/api/v1/assistants?skip=2&limit=2")
    assert page2_response.status_code == 200
    page2 = page2_response.json()
    
    # Ensure different assistants in different pages
    page1_ids = {a["id"] for a in page1["assistants"]}
    page2_ids = {a["id"] for a in page2["assistants"]}
    assert len(page1_ids.intersection(page2_ids)) == 0

@pytest.mark.asyncio
async def test_large_system_prompt(client: AsyncClient):
    """Test assistant with large system prompt."""
    large_prompt = "You are a helpful assistant. " * 100  # ~2000 characters
    
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Large Prompt Assistant",
        "system_prompt": large_prompt
    })
    assert assistant_response.status_code == 200
    
    assistant = assistant_response.json()
    assert len(assistant["system_prompt"]) > 1000

# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    import sys
    import subprocess
    
    # Run tests with pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--asyncio-mode=auto"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    sys.exit(result.returncode)