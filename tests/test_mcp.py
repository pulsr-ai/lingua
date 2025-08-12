"""
Comprehensive tests for MCP (Model Context Protocol) endpoints.
Tests all MCP server and tool operations.
"""

import pytest
from httpx import AsyncClient
from app.main import app
from typing import Dict, List
from uuid import UUID, uuid4

BASE_URL = "http://test"

# ============================================================================
# FIXTURES
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
async def sample_mcp_server():
    """Sample MCP server data for testing."""
    return {
        "name": "test_mcp_server",
        "url": "ws://localhost:3000/mcp",
        "protocol": "websocket",
        "api_key": "test_api_key_123"
    }

@pytest.fixture(scope="module")
async def registered_mcp_server(client: AsyncClient, sample_mcp_server: Dict):
    """Register a sample MCP server for testing."""
    # First try to delete if it exists
    list_response = await client.get("/api/v1/mcp/servers")
    if list_response.status_code == 200:
        servers = list_response.json()
        for server in servers:
            if server["name"] == sample_mcp_server["name"]:
                await client.delete(f"/api/v1/mcp/servers/{server['id']}")
                break
    
    response = await client.post("/api/v1/mcp/servers", json=sample_mcp_server)
    assert response.status_code == 200, f"Failed to register MCP server: {response.text}"
    return response.json()

# ============================================================================
# MCP SERVER MANAGEMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_mcp_server(client: AsyncClient):
    """Test creating a new MCP server."""
    server_data = {
        "name": "create_test_server",
        "url": "ws://localhost:3001/mcp",
        "protocol": "websocket",
        "api_key": "create_test_key"
    }
    
    # Clean up if exists
    list_response = await client.get("/api/v1/mcp/servers")
    if list_response.status_code == 200:
        servers = list_response.json()
        for server in servers:
            if server["name"] == server_data["name"]:
                await client.delete(f"/api/v1/mcp/servers/{server['id']}")
                break
    
    response = await client.post("/api/v1/mcp/servers", json=server_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == server_data["name"]
    assert data["url"] == server_data["url"] 
    assert data["protocol"] == server_data["protocol"]
    assert data["is_active"] is True
    assert data["connection_status"] == "disconnected"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    # API key should not be returned for security
    assert "api_key" not in data
    
    return data

@pytest.mark.asyncio
async def test_create_mcp_server_http(client: AsyncClient):
    """Test creating an MCP server with HTTP protocol."""
    server_data = {
        "name": "http_test_server",
        "url": "http://localhost:3002/mcp",
        "protocol": "http"
    }
    
    # Clean up if exists
    list_response = await client.get("/api/v1/mcp/servers")
    if list_response.status_code == 200:
        servers = list_response.json()
        for server in servers:
            if server["name"] == server_data["name"]:
                await client.delete(f"/api/v1/mcp/servers/{server['id']}")
                break
    
    response = await client.post("/api/v1/mcp/servers", json=server_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["protocol"] == "http"
    assert data["api_key"] is None

@pytest.mark.asyncio
async def test_create_mcp_server_duplicate_name(client: AsyncClient, registered_mcp_server: Dict):
    """Test creating an MCP server with duplicate name."""
    duplicate_data = {
        "name": registered_mcp_server["name"],
        "url": "ws://different.server.com/mcp",
        "protocol": "websocket"
    }
    
    response = await client.post("/api/v1/mcp/servers", json=duplicate_data)
    assert response.status_code == 400
    
    error_data = response.json()
    assert "detail" in error_data

@pytest.mark.asyncio
async def test_create_mcp_server_invalid_data(client: AsyncClient):
    """Test creating MCP server with invalid data."""
    # Missing required name
    response = await client.post("/api/v1/mcp/servers", json={
        "url": "ws://test.com/mcp",
        "protocol": "websocket"
    })
    assert response.status_code == 422
    
    # Missing required URL
    response = await client.post("/api/v1/mcp/servers", json={
        "name": "missing_url_server",
        "protocol": "websocket"
    })
    assert response.status_code == 422
    
    # Invalid protocol
    response = await client.post("/api/v1/mcp/servers", json={
        "name": "invalid_protocol_server",
        "url": "ws://test.com/mcp",
        "protocol": "invalid_protocol"
    })
    # Might succeed or fail depending on validation
    assert response.status_code in [200, 400, 422]

@pytest.mark.asyncio
async def test_list_mcp_servers(client: AsyncClient):
    """Test listing all MCP servers."""
    response = await client.get("/api/v1/mcp/servers")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Check structure of returned servers
    for server in data:
        assert "id" in server
        assert "name" in server
        assert "url" in server
        assert "protocol" in server
        assert "is_active" in server
        assert "connection_status" in server
        assert "created_at" in server
        assert "updated_at" in server
        # API key should not be returned
        assert "api_key" not in server

@pytest.mark.asyncio
async def test_update_mcp_server(client: AsyncClient, registered_mcp_server: Dict):
    """Test updating an MCP server."""
    update_data = {
        "url": "ws://updated.server.com/mcp",
        "protocol": "websocket",
        "is_active": False
    }
    
    response = await client.put(
        f"/api/v1/mcp/servers/{registered_mcp_server['id']}",
        json=update_data
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["url"] == update_data["url"]
    assert data["is_active"] == update_data["is_active"]
    assert data["name"] == registered_mcp_server["name"]  # Should not change
    assert data["id"] == registered_mcp_server["id"]  # Should not change

@pytest.mark.asyncio
async def test_update_nonexistent_mcp_server(client: AsyncClient):
    """Test updating a non-existent MCP server."""
    fake_id = str(uuid4())
    update_data = {"url": "ws://new.url.com/mcp"}
    
    response = await client.put(f"/api/v1/mcp/servers/{fake_id}", json=update_data)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_mcp_server(client: AsyncClient):
    """Test deleting an MCP server."""
    # First create a server to delete
    server_data = {
        "name": "delete_test_server",
        "url": "ws://to-be-deleted.com/mcp",
        "protocol": "websocket"
    }
    
    create_response = await client.post("/api/v1/mcp/servers", json=server_data)
    if create_response.status_code == 400:
        # Server might already exist, get it
        list_response = await client.get("/api/v1/mcp/servers")
        servers = list_response.json()
        server = next((s for s in servers if s["name"] == server_data["name"]), None)
        assert server is not None
    else:
        assert create_response.status_code == 200
        server = create_response.json()
    
    # Delete the server
    delete_response = await client.delete(f"/api/v1/mcp/servers/{server['id']}")
    assert delete_response.status_code == 200
    
    # Verify it's gone from the list
    list_response = await client.get("/api/v1/mcp/servers")
    assert list_response.status_code == 200
    servers = list_response.json()
    server_ids = [s["id"] for s in servers]
    assert server["id"] not in server_ids

@pytest.mark.asyncio
async def test_delete_nonexistent_mcp_server(client: AsyncClient):
    """Test deleting a non-existent MCP server."""
    fake_id = str(uuid4())
    response = await client.delete(f"/api/v1/mcp/servers/{fake_id}")
    assert response.status_code == 404

# ============================================================================
# MCP TOOLS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_list_mcp_tools(client: AsyncClient):
    """Test listing all available MCP tools."""
    response = await client.get("/api/v1/mcp/tools")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Check structure of tools (if any are available)
    for tool in data:
        assert "name" in tool
        assert "description" in tool
        assert "server" in tool
        assert "parameters" in tool

@pytest.mark.asyncio
async def test_execute_mcp_tool_nonexistent(client: AsyncClient):
    """Test executing a non-existent MCP tool."""
    execute_data = {"arguments": {}}
    
    response = await client.post("/api/v1/mcp/tools/nonexistent_tool/execute", json=execute_data)
    assert response.status_code == 404

# Note: We can't easily test successful MCP tool execution without a real MCP server
# running and connected, so we focus on error cases and structure validation

# ============================================================================
# VALIDATION AND ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_mcp_server_name_validation(client: AsyncClient):
    """Test MCP server name validation."""
    # Empty name
    response = await client.post("/api/v1/mcp/servers", json={
        "name": "",
        "url": "ws://test.com/mcp",
        "protocol": "websocket"
    })
    assert response.status_code == 422
    
    # Very long name
    long_name = "a" * 300
    response = await client.post("/api/v1/mcp/servers", json={
        "name": long_name,
        "url": "ws://test.com/mcp",
        "protocol": "websocket"
    })
    # Should either succeed or fail gracefully
    assert response.status_code in [200, 400, 422]

@pytest.mark.asyncio
async def test_mcp_server_url_validation(client: AsyncClient):
    """Test MCP server URL validation."""
    test_cases = [
        {
            "url": "",  # Empty URL
            "expected_status": 422
        },
        {
            "url": "not-a-url",  # Invalid URL format
            "expected_status": [200, 400, 422]  # Depends on validation level
        },
        {
            "url": "ftp://invalid-protocol.com/mcp",  # Unusual protocol
            "expected_status": [200, 400, 422]  # Depends on validation level
        },
        {
            "url": "ws://valid.server.com/mcp",  # Valid websocket URL
            "expected_status": 200
        },
        {
            "url": "http://valid.server.com/mcp",  # Valid HTTP URL
            "expected_status": 200
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        server_data = {
            "name": f"url_validation_test_{i}",
            "url": test_case["url"],
            "protocol": "websocket"
        }
        
        # Clean up first
        list_response = await client.get("/api/v1/mcp/servers")
        if list_response.status_code == 200:
            servers = list_response.json()
            for server in servers:
                if server["name"] == server_data["name"]:
                    await client.delete(f"/api/v1/mcp/servers/{server['id']}")
                    break
        
        response = await client.post("/api/v1/mcp/servers", json=server_data)
        
        expected = test_case["expected_status"]
        if isinstance(expected, list):
            assert response.status_code in expected
        else:
            assert response.status_code == expected

@pytest.mark.asyncio
async def test_invalid_uuid_mcp_operations(client: AsyncClient):
    """Test MCP operations with invalid UUIDs."""
    invalid_uuid = "not-a-uuid"
    
    # Update with invalid UUID
    response = await client.put(f"/api/v1/mcp/servers/{invalid_uuid}", json={
        "url": "ws://test.com/mcp"
    })
    assert response.status_code == 422
    
    # Delete with invalid UUID
    response = await client.delete(f"/api/v1/mcp/servers/{invalid_uuid}")
    assert response.status_code == 422

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_mcp_server_lifecycle(client: AsyncClient):
    """Test the complete lifecycle of an MCP server."""
    server_data = {
        "name": "lifecycle_test_server",
        "url": "ws://lifecycle.test.com/mcp",
        "protocol": "websocket",
        "api_key": "lifecycle_key"
    }
    
    # Step 1: Create server
    create_response = await client.post("/api/v1/mcp/servers", json=server_data)
    if create_response.status_code == 400:
        # Server exists, delete it first
        list_response = await client.get("/api/v1/mcp/servers")
        servers = list_response.json()
        existing = next((s for s in servers if s["name"] == server_data["name"]), None)
        if existing:
            await client.delete(f"/api/v1/mcp/servers/{existing['id']}")
        create_response = await client.post("/api/v1/mcp/servers", json=server_data)
    
    assert create_response.status_code == 200
    server = create_response.json()
    server_id = server["id"]
    
    # Step 2: Verify it appears in list
    list_response = await client.get("/api/v1/mcp/servers")
    assert list_response.status_code == 200
    servers = list_response.json()
    server_ids = [s["id"] for s in servers]
    assert server_id in server_ids
    
    # Step 3: Update server
    update_data = {
        "url": "ws://updated.lifecycle.test.com/mcp",
        "is_active": False
    }
    update_response = await client.put(f"/api/v1/mcp/servers/{server_id}", json=update_data)
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["url"] == update_data["url"]
    assert updated["is_active"] == update_data["is_active"]
    
    # Step 4: Delete server
    delete_response = await client.delete(f"/api/v1/mcp/servers/{server_id}")
    assert delete_response.status_code == 200
    
    # Step 5: Verify it's gone
    final_list_response = await client.get("/api/v1/mcp/servers")
    assert final_list_response.status_code == 200
    final_servers = final_list_response.json()
    final_server_ids = [s["id"] for s in final_servers]
    assert server_id not in final_server_ids

@pytest.mark.asyncio
async def test_multiple_mcp_servers(client: AsyncClient):
    """Test managing multiple MCP servers."""
    servers_data = [
        {
            "name": "multi_test_server_1",
            "url": "ws://server1.test.com/mcp",
            "protocol": "websocket"
        },
        {
            "name": "multi_test_server_2",
            "url": "http://server2.test.com/mcp",
            "protocol": "http"
        },
        {
            "name": "multi_test_server_3",
            "url": "ws://server3.test.com/mcp",
            "protocol": "websocket",
            "api_key": "server3_key"
        }
    ]
    
    created_servers = []
    
    # Create all servers
    for server_data in servers_data:
        # Clean up if exists
        list_response = await client.get("/api/v1/mcp/servers")
        if list_response.status_code == 200:
            existing_servers = list_response.json()
            for existing in existing_servers:
                if existing["name"] == server_data["name"]:
                    await client.delete(f"/api/v1/mcp/servers/{existing['id']}")
                    break
        
        response = await client.post("/api/v1/mcp/servers", json=server_data)
        assert response.status_code == 200
        created_servers.append(response.json())
    
    # Verify all are in the list
    list_response = await client.get("/api/v1/mcp/servers")
    assert list_response.status_code == 200
    all_servers = list_response.json()
    all_server_ids = [s["id"] for s in all_servers]
    
    for created in created_servers:
        assert created["id"] in all_server_ids
    
    # Clean up - delete all created servers
    for created in created_servers:
        delete_response = await client.delete(f"/api/v1/mcp/servers/{created['id']}")
        assert delete_response.status_code == 200

@pytest.mark.asyncio
async def test_mcp_server_security(client: AsyncClient):
    """Test that API keys are handled securely."""
    server_data = {
        "name": "security_test_server",
        "url": "ws://security.test.com/mcp",
        "protocol": "websocket",
        "api_key": "super_secret_key_do_not_expose"
    }
    
    # Clean up if exists
    list_response = await client.get("/api/v1/mcp/servers")
    if list_response.status_code == 200:
        servers = list_response.json()
        for server in servers:
            if server["name"] == server_data["name"]:
                await client.delete(f"/api/v1/mcp/servers/{server['id']}")
                break
    
    # Create server with API key
    create_response = await client.post("/api/v1/mcp/servers", json=server_data)
    assert create_response.status_code == 200
    
    created = create_response.json()
    # API key should not be returned in response
    assert "api_key" not in created
    
    # API key should not appear in list either
    list_response = await client.get("/api/v1/mcp/servers")
    assert list_response.status_code == 200
    servers = list_response.json()
    
    for server in servers:
        assert "api_key" not in server
    
    # Clean up
    await client.delete(f"/api/v1/mcp/servers/{created['id']}")

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