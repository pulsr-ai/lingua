"""
Comprehensive tests for Chat endpoints.
Tests all chat-related operations including creation, listing, updates, and deletion.
"""

import pytest
from httpx import AsyncClient
from app.main import app
from typing import Dict
from uuid import UUID, uuid4

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
async def test_subtenant(client: AsyncClient):
    response = await client.post("/api/v1/subtenants/", json={})
    assert response.status_code == 200
    return response.json()

@pytest.mark.asyncio
async def test_create_chat(client: AsyncClient, test_subtenant: Dict):
    chat_data = {
        "title": "Test Chat",
        "system_message": "You are a helpful assistant."
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/chats",
        json=chat_data
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == chat_data["title"]
    assert "id" in data
    assert data["subtenant_id"] == test_subtenant["id"]
    
    return data

@pytest.mark.asyncio
async def test_list_chats(client: AsyncClient, test_subtenant: Dict):
    response = await client.get(f"/api/v1/subtenants/{test_subtenant['id']}/chats")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_chat(client: AsyncClient, test_subtenant: Dict):
    create_response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/chats",
        json={"title": "Get Test Chat"}
    )
    assert create_response.status_code == 200
    chat = create_response.json()
    
    get_response = await client.get(f"/api/v1/chats/{chat['id']}")
    assert get_response.status_code == 200
    
    retrieved = get_response.json()
    assert retrieved["id"] == chat["id"]
    assert retrieved["title"] == "Get Test Chat"

@pytest.mark.asyncio
async def test_update_chat(client: AsyncClient, test_subtenant: Dict):
    create_response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/chats",
        json={"title": "Original Title"}
    )
    assert create_response.status_code == 200
    chat = create_response.json()
    
    update_response = await client.put(
        f"/api/v1/chats/{chat['id']}",
        json={"title": "Updated Title"}
    )
    assert update_response.status_code == 200
    
    updated = update_response.json()
    assert updated["title"] == "Updated Title"
    assert updated["id"] == chat["id"]

@pytest.mark.asyncio
async def test_delete_chat(client: AsyncClient, test_subtenant: Dict):
    create_response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/chats",
        json={"title": "To Be Deleted"}
    )
    assert create_response.status_code == 200
    chat = create_response.json()
    
    delete_response = await client.delete(f"/api/v1/chats/{chat['id']}")
    assert delete_response.status_code == 200
    
    get_response = await client.get(f"/api/v1/chats/{chat['id']}")
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_chat_with_assistant(client: AsyncClient, test_subtenant: Dict):
    # Create an assistant first
    assistant_response = await client.post("/api/v1/assistants", json={
        "name": "Chat Test Assistant",
        "system_prompt": "You are a test assistant."
    })
    
    if assistant_response.status_code == 200:
        assistant = assistant_response.json()
        
        # Create chat with assistant
        chat_response = await client.post(
            f"/api/v1/subtenants/{test_subtenant['id']}/chats",
            json={
                "title": "Assistant Chat",
                "assistant_id": assistant["id"]
            }
        )
        assert chat_response.status_code == 200
        
        chat = chat_response.json()
        assert chat["assistant_id"] == assistant["id"]

@pytest.mark.asyncio
async def test_invalid_subtenant_chat_operations(client: AsyncClient):
    fake_id = str(uuid4())
    
    # Create chat with invalid subtenant
    response = await client.post(
        f"/api/v1/subtenants/{fake_id}/chats",
        json={"title": "Invalid"}
    )
    assert response.status_code == 404
    
    # List chats for invalid subtenant
    response = await client.get(f"/api/v1/subtenants/{fake_id}/chats")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_invalid_chat_operations(client: AsyncClient):
    fake_id = str(uuid4())
    
    # Get invalid chat
    response = await client.get(f"/api/v1/chats/{fake_id}")
    assert response.status_code == 404
    
    # Update invalid chat
    response = await client.put(f"/api/v1/chats/{fake_id}", json={"title": "Updated"})
    assert response.status_code == 404
    
    # Delete invalid chat
    response = await client.delete(f"/api/v1/chats/{fake_id}")
    assert response.status_code == 404

if __name__ == "__main__":
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr: print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)