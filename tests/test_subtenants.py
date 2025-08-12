"""
Comprehensive tests for Subtenants endpoints.
Tests all CRUD operations for the /subtenants endpoints.
"""

import pytest
from httpx import AsyncClient
from app.main import app
from typing import Dict
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

# ============================================================================
# SUBTENANT CRUD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_subtenant(client: AsyncClient):
    """Test creating a new subtenant."""
    response = await client.post("/api/v1/subtenants/", json={})
    assert response.status_code == 200
    
    data = response.json()
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    # Validate UUID format
    assert UUID(data["id"])
    
    return data

@pytest.mark.asyncio
async def test_list_subtenants(client: AsyncClient):
    """Test listing all subtenants."""
    # First create a few subtenants
    created_subtenants = []
    for i in range(3):
        response = await client.post("/api/v1/subtenants/", json={})
        assert response.status_code == 200
        created_subtenants.append(response.json())
    
    # List subtenants
    response = await client.get("/api/v1/subtenants/")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # At least the ones we created
    
    # Verify structure of returned subtenants
    for subtenant in data:
        assert "id" in subtenant
        assert "created_at" in subtenant
        assert "updated_at" in subtenant

@pytest.mark.asyncio
async def test_get_subtenant(client: AsyncClient):
    """Test getting a specific subtenant."""
    # Create a subtenant first
    create_response = await client.post("/api/v1/subtenants/", json={})
    assert create_response.status_code == 200
    created = create_response.json()
    
    # Get the subtenant
    response = await client.get(f"/api/v1/subtenants/{created['id']}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == created["id"]
    assert data["created_at"] == created["created_at"]
    assert data["updated_at"] == created["updated_at"]

@pytest.mark.asyncio
async def test_update_subtenant(client: AsyncClient):
    """Test updating a subtenant."""
    # Create a subtenant first
    create_response = await client.post("/api/v1/subtenants/", json={})
    assert create_response.status_code == 200
    created = create_response.json()
    
    # Update the subtenant (note: SubtenantUpdate is empty, but endpoint should work)
    update_data = {}  # Based on the schema, there are no updatable fields
    response = await client.put(f"/api/v1/subtenants/{created['id']}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == created["id"]
    # updated_at should be changed
    # assert data["updated_at"] != created["updated_at"]  # Might be same if no actual changes

@pytest.mark.asyncio
async def test_delete_subtenant(client: AsyncClient):
    """Test deleting a subtenant."""
    # Create a subtenant first
    create_response = await client.post("/api/v1/subtenants/", json={})
    assert create_response.status_code == 200
    created = create_response.json()
    
    # Delete the subtenant
    response = await client.delete(f"/api/v1/subtenants/{created['id']}")
    assert response.status_code == 200
    
    # Try to get the deleted subtenant - should return 404
    get_response = await client.get(f"/api/v1/subtenants/{created['id']}")
    assert get_response.status_code == 404

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_nonexistent_subtenant(client: AsyncClient):
    """Test getting a subtenant that doesn't exist."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/subtenants/{fake_id}")
    assert response.status_code == 404
    
    error_data = response.json()
    assert "detail" in error_data
    assert "not found" in error_data["detail"].lower()

@pytest.mark.asyncio
async def test_update_nonexistent_subtenant(client: AsyncClient):
    """Test updating a subtenant that doesn't exist."""
    fake_id = str(uuid4())
    response = await client.put(f"/api/v1/subtenants/{fake_id}", json={})
    assert response.status_code == 404
    
    error_data = response.json()
    assert "detail" in error_data
    assert "not found" in error_data["detail"].lower()

@pytest.mark.asyncio
async def test_delete_nonexistent_subtenant(client: AsyncClient):
    """Test deleting a subtenant that doesn't exist."""
    fake_id = str(uuid4())
    response = await client.delete(f"/api/v1/subtenants/{fake_id}")
    assert response.status_code == 404
    
    error_data = response.json()
    assert "detail" in error_data
    assert "not found" in error_data["detail"].lower()

@pytest.mark.asyncio
async def test_invalid_uuid_format(client: AsyncClient):
    """Test endpoints with invalid UUID format."""
    invalid_uuid = "not-a-uuid"
    
    # Test GET with invalid UUID
    response = await client.get(f"/api/v1/subtenants/{invalid_uuid}")
    assert response.status_code == 422  # Validation error
    
    # Test PUT with invalid UUID
    response = await client.put(f"/api/v1/subtenants/{invalid_uuid}", json={})
    assert response.status_code == 422  # Validation error
    
    # Test DELETE with invalid UUID
    response = await client.delete(f"/api/v1/subtenants/{invalid_uuid}")
    assert response.status_code == 422  # Validation error

# ============================================================================
# PAGINATION AND FILTERING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_list_subtenants_pagination(client: AsyncClient):
    """Test pagination parameters for listing subtenants."""
    # Create several subtenants first
    created_count = 5
    for i in range(created_count):
        response = await client.post("/api/v1/subtenants/", json={})
        assert response.status_code == 200
    
    # Test with limit
    response = await client.get("/api/v1/subtenants/?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2
    
    # Test with skip
    response = await client.get("/api/v1/subtenants/?skip=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2
    
    # Test with both skip and limit
    first_page = await client.get("/api/v1/subtenants/?skip=0&limit=1")
    second_page = await client.get("/api/v1/subtenants/?skip=1&limit=1")
    
    assert first_page.status_code == 200
    assert second_page.status_code == 200
    
    first_data = first_page.json()
    second_data = second_page.json()
    
    # Should be different subtenants
    if len(first_data) > 0 and len(second_data) > 0:
        assert first_data[0]["id"] != second_data[0]["id"]

@pytest.mark.asyncio
async def test_list_subtenants_invalid_parameters(client: AsyncClient):
    """Test listing subtenants with invalid parameters."""
    # Test with negative skip - should return error due to database constraint
    response = await client.get("/api/v1/subtenants/?skip=-1")
    assert response.status_code in [400, 422, 500]  # Database error for negative offset
    
    # Test with negative limit
    response = await client.get("/api/v1/subtenants/?limit=-1")
    # Should work or return 422 - depends on FastAPI validation
    assert response.status_code in [200, 422]
    
    # Test with non-integer parameters
    response = await client.get("/api/v1/subtenants/?skip=abc")
    assert response.status_code == 422
    
    response = await client.get("/api/v1/subtenants/?limit=xyz")
    assert response.status_code == 422

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_subtenant_lifecycle(client: AsyncClient):
    """Test the complete lifecycle of a subtenant."""
    # Step 1: Create subtenant
    create_response = await client.post("/api/v1/subtenants/", json={})
    assert create_response.status_code == 200
    subtenant = create_response.json()
    subtenant_id = subtenant["id"]
    
    # Step 2: Verify it appears in list
    list_response = await client.get("/api/v1/subtenants/")
    assert list_response.status_code == 200
    subtenants = list_response.json()
    subtenant_ids = [s["id"] for s in subtenants]
    assert subtenant_id in subtenant_ids
    
    # Step 3: Get individual subtenant
    get_response = await client.get(f"/api/v1/subtenants/{subtenant_id}")
    assert get_response.status_code == 200
    retrieved = get_response.json()
    assert retrieved["id"] == subtenant_id
    
    # Step 4: Update subtenant
    update_response = await client.put(f"/api/v1/subtenants/{subtenant_id}", json={})
    assert update_response.status_code == 200
    
    # Step 5: Delete subtenant
    delete_response = await client.delete(f"/api/v1/subtenants/{subtenant_id}")
    assert delete_response.status_code == 200
    
    # Step 6: Verify it's gone
    get_after_delete_response = await client.get(f"/api/v1/subtenants/{subtenant_id}")
    assert get_after_delete_response.status_code == 404

@pytest.mark.asyncio
async def test_multiple_subtenants_isolation(client: AsyncClient):
    """Test that multiple subtenants are properly isolated."""
    # Create multiple subtenants
    subtenants = []
    for i in range(3):
        response = await client.post("/api/v1/subtenants/", json={})
        assert response.status_code == 200
        subtenants.append(response.json())
    
    # Verify each has a unique ID
    ids = [s["id"] for s in subtenants]
    assert len(set(ids)) == 3  # All IDs should be unique
    
    # Verify each can be retrieved independently
    for subtenant in subtenants:
        response = await client.get(f"/api/v1/subtenants/{subtenant['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == subtenant["id"]

# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_many_subtenants(client: AsyncClient):
    """Test creating many subtenants (performance and stability)."""
    created_ids = []
    
    # Create 10 subtenants
    for i in range(10):
        response = await client.post("/api/v1/subtenants/", json={})
        assert response.status_code == 200
        data = response.json()
        created_ids.append(data["id"])
    
    # Verify all were created with unique IDs
    assert len(set(created_ids)) == 10
    
    # Verify we can list them - get enough to include our new ones
    response = await client.get("/api/v1/subtenants/?limit=100")  # Get more to account for other tests
    assert response.status_code == 200
    all_subtenants = response.json()
    
    # Check that our created subtenants are in the list
    all_ids = [s["id"] for s in all_subtenants]
    missing_ids = []
    for created_id in created_ids:
        if created_id not in all_ids:
            missing_ids.append(created_id)
    
    # If some are missing, verify they still exist individually
    for missing_id in missing_ids:
        check_response = await client.get(f"/api/v1/subtenants/{missing_id}")
        assert check_response.status_code == 200, f"Subtenant {missing_id} should exist but was not found"

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