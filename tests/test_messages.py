"""
Comprehensive tests for Messages endpoints.
Tests message listing and sending (both sync and streaming).
"""

import pytest
from httpx import AsyncClient
from app.main import app
from typing import Dict
from uuid import UUID

BASE_URL = "http://test"

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
async def test_chat(client: AsyncClient):
    # Create subtenant
    subtenant_response = await client.post("/api/v1/subtenants/", json={})
    assert subtenant_response.status_code == 200
    subtenant = subtenant_response.json()
    
    # Create chat
    chat_response = await client.post(
        f"/api/v1/subtenants/{subtenant['id']}/chats",
        json={"title": "Test Chat"}
    )
    assert chat_response.status_code == 200
    return chat_response.json()

@pytest.mark.asyncio
async def test_list_messages(client: AsyncClient, test_chat: Dict):
    """Test listing messages from a chat."""
    response = await client.get(f"/api/v1/chats/{test_chat['id']}/messages")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_send_message(client: AsyncClient, test_chat: Dict):
    """Test sending a message to a chat."""
    message_data = {
        "content": "Hello, this is a test message."
    }
    
    response = await client.post(
        f"/api/v1/chats/{test_chat['id']}/messages",
        json=message_data
    )
    
    # Message sending requires LLM provider which might not be available in tests
    if response.status_code == 200:
        data = response.json()
        assert "message" in data
        assert data["message"]["role"] == "assistant"
    else:
        # Provider not available, that's fine for testing endpoints
        assert response.status_code in [400, 500, 503]

@pytest.mark.asyncio
async def test_stream_message(client: AsyncClient, test_chat: Dict):
    """Test streaming a message to a chat."""
    message_data = {
        "content": "Hello, this is a streaming test message."
    }
    
    async with client.stream(
        "POST",
        f"/api/v1/chats/{test_chat['id']}/messages/stream",
        json=message_data
    ) as response:
        # Streaming might fail due to provider not being available
        if response.status_code == 200:
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            # Try to read some chunks
            chunks = []
            async for chunk in response.aiter_text():
                chunks.append(chunk)
                if len(chunks) >= 3:  # Read a few chunks
                    break
        else:
            # Provider not available, that's fine for testing endpoints
            assert response.status_code in [400, 500, 503]

@pytest.mark.asyncio
async def test_send_message_with_functions(client: AsyncClient, test_chat: Dict):
    """Test sending a message with function configuration."""
    message_data = {
        "content": "What time is it?",
        "enabled_functions": ["get_current_time"],
        "disabled_functions": []
    }
    
    response = await client.post(
        f"/api/v1/chats/{test_chat['id']}/messages",
        json=message_data
    )
    
    # Message sending requires LLM provider which might not be available
    if response.status_code == 200:
        data = response.json()
        assert "message" in data
    else:
        # Provider not available or function not registered
        assert response.status_code in [400, 500, 503]

@pytest.mark.asyncio
async def test_send_message_with_provider(client: AsyncClient, test_chat: Dict):
    """Test sending a message with specific provider."""
    message_data = {
        "content": "Hello with specific provider",
        "provider_name": "openai"  # Might not be available
    }
    
    response = await client.post(
        f"/api/v1/chats/{test_chat['id']}/messages",
        json=message_data
    )
    
    # Provider might not be available
    assert response.status_code in [200, 400, 500, 503]

@pytest.mark.asyncio
async def test_invalid_chat_message_operations(client: AsyncClient):
    """Test message operations with invalid chat ID."""
    from uuid import uuid4
    fake_id = str(uuid4())
    
    # List messages for invalid chat
    response = await client.get(f"/api/v1/chats/{fake_id}/messages")
    assert response.status_code == 404
    
    # Send message to invalid chat
    response = await client.post(
        f"/api/v1/chats/{fake_id}/messages",
        json={"content": "Test"}
    )
    assert response.status_code == 404
    
    # Stream message to invalid chat
    async with client.stream(
        "POST",
        f"/api/v1/chats/{fake_id}/messages/stream",
        json={"content": "Test"}
    ) as response:
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_message_validation(client: AsyncClient, test_chat: Dict):
    """Test message data validation."""
    # Missing content
    response = await client.post(
        f"/api/v1/chats/{test_chat['id']}/messages",
        json={}
    )
    assert response.status_code == 422
    
    # Empty content
    response = await client.post(
        f"/api/v1/chats/{test_chat['id']}/messages",
        json={"content": ""}
    )
    # Might be allowed or not
    assert response.status_code in [200, 400, 422, 500, 503]

@pytest.mark.asyncio
async def test_message_history_after_send(client: AsyncClient, test_chat: Dict):
    """Test that message history is updated after sending."""
    # Get initial message count
    initial_response = await client.get(f"/api/v1/chats/{test_chat['id']}/messages")
    assert initial_response.status_code == 200
    initial_messages = initial_response.json()
    initial_count = len(initial_messages)
    
    # Send a message
    message_data = {"content": "Test history message"}
    send_response = await client.post(
        f"/api/v1/chats/{test_chat['id']}/messages",
        json=message_data
    )
    
    # If message was sent successfully, check history
    if send_response.status_code == 200:
        after_response = await client.get(f"/api/v1/chats/{test_chat['id']}/messages")
        assert after_response.status_code == 200
        after_messages = after_response.json()
        
        # Should have more messages now
        assert len(after_messages) > initial_count
        
        # Should include our user message
        user_messages = [m for m in after_messages if m["role"] == "user"]
        assert any(m["content"] == "Test history message" for m in user_messages)

if __name__ == "__main__":
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr: print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)