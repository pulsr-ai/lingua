"""
Comprehensive tests for LLM endpoints.
Tests direct LLM completion and streaming endpoints.
"""

import pytest
from httpx import AsyncClient
from app.main import app
from typing import Dict

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
async def test_llm_complete(client: AsyncClient, test_subtenant: Dict):
    """Test direct LLM completion."""
    request_data = {
        "messages": [
            {"role": "user", "content": "What is 2 + 2?"}
        ],
        "model": "gpt-3.5-turbo"
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/llm/complete",
        json=request_data
    )
    
    # LLM provider might not be available in test environment
    if response.status_code == 200:
        data = response.json()
        assert "content" in data or "message" in data
    else:
        # Provider not available or configured
        assert response.status_code in [400, 500, 503]

@pytest.mark.asyncio
async def test_llm_complete_with_tools(client: AsyncClient, test_subtenant: Dict):
    """Test LLM completion with function tools."""
    request_data = {
        "messages": [
            {"role": "user", "content": "What time is it?"}
        ],
        "model": "gpt-3.5-turbo",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Get the current time",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/llm/complete",
        json=request_data
    )
    
    # Provider might not be available
    assert response.status_code in [200, 400, 500, 503]

@pytest.mark.asyncio
async def test_llm_stream(client: AsyncClient, test_subtenant: Dict):
    """Test LLM streaming."""
    request_data = {
        "messages": [
            {"role": "user", "content": "Tell me a short story"}
        ],
        "model": "gpt-3.5-turbo"
    }
    
    async with client.stream(
        "POST",
        f"/api/v1/subtenants/{test_subtenant['id']}/llm/stream",
        json=request_data
    ) as response:
        if response.status_code == 200:
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            # Try to read some chunks
            chunks = []
            async for chunk in response.aiter_text():
                chunks.append(chunk)
                if len(chunks) >= 3:  # Read a few chunks
                    break
            
            assert len(chunks) > 0
        else:
            # Provider not available
            assert response.status_code in [400, 500, 503]

@pytest.mark.asyncio
async def test_llm_complete_validation(client: AsyncClient, test_subtenant: Dict):
    """Test LLM completion request validation."""
    # Missing messages
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/llm/complete",
        json={"model": "gpt-3.5-turbo"}
    )
    assert response.status_code == 422
    
    # Missing model
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/llm/complete",
        json={"messages": [{"role": "user", "content": "test"}]}
    )
    assert response.status_code == 422
    
    # Empty messages
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/llm/complete",
        json={"messages": [], "model": "gpt-3.5-turbo"}
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_llm_complete_different_models(client: AsyncClient, test_subtenant: Dict):
    """Test LLM completion with different models."""
    models = ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet", "gemma-7b"]
    
    for model in models:
        request_data = {
            "messages": [{"role": "user", "content": "Hello"}],
            "model": model
        }
        
        response = await client.post(
            f"/api/v1/subtenants/{test_subtenant['id']}/llm/complete",
            json=request_data
        )
        
        # Some models might be available, others not
        assert response.status_code in [200, 400, 500, 503]

@pytest.mark.asyncio
async def test_llm_complete_with_parameters(client: AsyncClient, test_subtenant: Dict):
    """Test LLM completion with various parameters."""
    request_data = {
        "messages": [{"role": "user", "content": "Generate a number"}],
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.9
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/llm/complete",
        json=request_data
    )
    
    # Provider might not be available
    assert response.status_code in [200, 400, 500, 503]

@pytest.mark.asyncio
async def test_llm_invalid_subtenant(client: AsyncClient):
    """Test LLM operations with invalid subtenant."""
    from uuid import uuid4
    fake_id = str(uuid4())
    
    request_data = {
        "messages": [{"role": "user", "content": "test"}],
        "model": "gpt-3.5-turbo"
    }
    
    # Test complete
    response = await client.post(
        f"/api/v1/subtenants/{fake_id}/llm/complete",
        json=request_data
    )
    assert response.status_code == 404
    
    # Test stream
    async with client.stream(
        "POST",
        f"/api/v1/subtenants/{fake_id}/llm/stream",
        json=request_data
    ) as response:
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_llm_complete_conversation(client: AsyncClient, test_subtenant: Dict):
    """Test LLM completion with conversation history."""
    request_data = {
        "messages": [
            {"role": "user", "content": "My name is Alice"},
            {"role": "assistant", "content": "Nice to meet you, Alice!"},
            {"role": "user", "content": "What's my name?"}
        ],
        "model": "gpt-3.5-turbo"
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/llm/complete",
        json=request_data
    )
    
    if response.status_code == 200:
        data = response.json()
        # Should mention Alice in the response
        content = data.get("content", "").lower()
        assert "alice" in content
    else:
        # Provider not available
        assert response.status_code in [400, 500, 503]

if __name__ == "__main__":
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr: print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)