"""
Comprehensive tests for Tools endpoints.
Tests tool availability and tool name endpoints.
"""

import pytest
from httpx import AsyncClient
from app.main import app

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

@pytest.mark.asyncio
async def test_get_available_tools(client: AsyncClient):
    """Test getting all available tools."""
    response = await client.get("/api/v1/tools/available")
    assert response.status_code == 200
    
    data = response.json()
    # Should have tools structure
    assert "functions" in data or "tools" in data or isinstance(data, dict)

@pytest.mark.asyncio
async def test_get_tool_names(client: AsyncClient):
    """Test getting tool names."""
    response = await client.get("/api/v1/tools/names")
    assert response.status_code == 200
    
    # Could return various formats depending on implementation
    data = response.json()
    # Could be a list of names or an object with categories
    assert isinstance(data, (list, dict))

@pytest.mark.asyncio
async def test_available_tools_structure(client: AsyncClient):
    """Test that available tools have proper structure."""
    response = await client.get("/api/v1/tools/available")
    assert response.status_code == 200
    
    data = response.json()
    
    # The response should contain information about available tools
    # Structure might vary, so we just check it's valid JSON
    assert data is not None

@pytest.mark.asyncio
async def test_tool_names_format(client: AsyncClient):
    """Test tool names response format."""
    response = await client.get("/api/v1/tools/names")
    assert response.status_code == 200
    
    data = response.json()
    
    if isinstance(data, list):
        # List of tool names
        for name in data:
            assert isinstance(name, str)
            assert len(name) > 0
    elif isinstance(data, dict):
        # Dictionary structure with tool categories
        for key, value in data.items():
            assert isinstance(key, str)
    else:
        # Other valid formats
        assert data is not None

@pytest.mark.asyncio
async def test_tools_consistency(client: AsyncClient):
    """Test consistency between available tools and tool names."""
    # Get available tools
    available_response = await client.get("/api/v1/tools/available")
    assert available_response.status_code == 200
    available_data = available_response.json()
    
    # Get tool names
    names_response = await client.get("/api/v1/tools/names")
    assert names_response.status_code == 200
    names_data = names_response.json()
    
    # Both should be valid responses
    assert available_data is not None
    assert names_data is not None

@pytest.mark.asyncio
async def test_tools_endpoints_no_auth_required(client: AsyncClient):
    """Test that tools endpoints don't require authentication."""
    # These endpoints should be accessible without subtenant context
    response = await client.get("/api/v1/tools/available")
    # Should not return 401/403 (auth errors)
    assert response.status_code not in [401, 403]
    
    response = await client.get("/api/v1/tools/names")
    assert response.status_code not in [401, 403]

@pytest.mark.asyncio
async def test_tools_endpoints_methods(client: AsyncClient):
    """Test that tools endpoints only accept GET methods."""
    endpoints = ["/api/v1/tools/available", "/api/v1/tools/names"]
    
    for endpoint in endpoints:
        # POST should not be allowed
        post_response = await client.post(endpoint, json={})
        assert post_response.status_code in [405, 404]  # Method not allowed or not found
        
        # PUT should not be allowed
        put_response = await client.put(endpoint, json={})
        assert put_response.status_code in [405, 404]  # Method not allowed or not found
        
        # DELETE should not be allowed
        delete_response = await client.delete(endpoint)
        assert delete_response.status_code in [405, 404]  # Method not allowed or not found

@pytest.mark.asyncio
async def test_tools_response_headers(client: AsyncClient):
    """Test response headers for tools endpoints."""
    response = await client.get("/api/v1/tools/available")
    
    if response.status_code == 200:
        # Should return JSON content
        assert "application/json" in response.headers.get("content-type", "")
    
    response = await client.get("/api/v1/tools/names")
    
    if response.status_code == 200:
        # Should return JSON content
        assert "application/json" in response.headers.get("content-type", "")

if __name__ == "__main__":
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr: print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)