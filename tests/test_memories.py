"""
Comprehensive tests for Memories endpoints.
Tests all memory management operations for subtenants.
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
async def test_subtenant(client: AsyncClient):
    """Create a test subtenant for memory operations."""
    response = await client.post("/api/v1/subtenants/", json={})
    assert response.status_code == 200
    return response.json()

@pytest.fixture(scope="module")
async def second_subtenant(client: AsyncClient):
    """Create a second test subtenant for isolation testing."""
    response = await client.post("/api/v1/subtenants/", json={})
    assert response.status_code == 200
    return response.json()

# ============================================================================
# MEMORY CRUD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_memory(client: AsyncClient, test_subtenant: Dict):
    """Test creating a new memory."""
    memory_data = {
        "key": "test_key",
        "value": "This is a test memory value"
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json=memory_data
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["key"] == memory_data["key"]
    assert data["value"] == memory_data["value"]
    assert "created_at" in data
    assert "updated_at" in data
    
    return data

@pytest.mark.asyncio
async def test_create_memory_duplicate_key(client: AsyncClient, test_subtenant: Dict):
    """Test creating a memory with duplicate key (should update existing)."""
    memory_data = {
        "key": "duplicate_test_key",
        "value": "First value"
    }
    
    # Create first memory
    response1 = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json=memory_data
    )
    assert response1.status_code == 200
    first_memory = response1.json()
    
    # Create second memory with same key
    updated_memory_data = {
        "key": "duplicate_test_key",
        "value": "Updated value"
    }
    
    response2 = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json=updated_memory_data
    )
    
    # Should either create new or update existing - both are valid behaviors
    assert response2.status_code in [200, 400, 409]
    
    if response2.status_code == 200:
        # If creation succeeded, verify the value
        second_memory = response2.json()
        # Could be the same memory updated or a new one created
        assert second_memory["key"] == updated_memory_data["key"]

@pytest.mark.asyncio
async def test_list_memories(client: AsyncClient, test_subtenant: Dict):
    """Test listing all memories for a subtenant."""
    # Create a few memories first
    memories_data = [
        {"key": "list_test_1", "value": "Value 1"},
        {"key": "list_test_2", "value": "Value 2"},
        {"key": "list_test_3", "value": "Value 3"}
    ]
    
    created_memories = []
    for memory_data in memories_data:
        response = await client.post(
            f"/api/v1/subtenants/{test_subtenant['id']}/memories",
            json=memory_data
        )
        if response.status_code == 200:
            created_memories.append(response.json())
    
    # List all memories
    list_response = await client.get(f"/api/v1/subtenants/{test_subtenant['id']}/memories")
    assert list_response.status_code == 200
    
    memories = list_response.json()
    assert isinstance(memories, list)
    assert len(memories) >= len(created_memories)
    
    # Verify our created memories are in the list
    memory_keys = [m["key"] for m in memories]
    for created in created_memories:
        assert created["key"] in memory_keys

@pytest.mark.asyncio
async def test_get_memory(client: AsyncClient, test_subtenant: Dict):
    """Test getting a specific memory."""
    # Create a memory first
    memory_data = {
        "key": "get_test_key",
        "value": "Get test value"
    }
    
    create_response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json=memory_data
    )
    assert create_response.status_code == 200
    
    # Get the memory
    get_response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_data['key']}"
    )
    assert get_response.status_code == 200
    
    retrieved = get_response.json()
    assert retrieved["key"] == memory_data["key"]
    assert retrieved["value"] == memory_data["value"]

@pytest.mark.asyncio
async def test_update_memory(client: AsyncClient, test_subtenant: Dict):
    """Test updating an existing memory."""
    # Create a memory first
    memory_data = {
        "key": "update_test_key",
        "value": "Original value"
    }
    
    create_response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json=memory_data
    )
    assert create_response.status_code == 200
    original = create_response.json()
    
    # Update the memory
    update_data = {
        "value": "Updated value"
    }
    
    update_response = await client.put(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_data['key']}",
        json=update_data
    )
    assert update_response.status_code == 200
    
    updated = update_response.json()
    assert updated["key"] == memory_data["key"]
    assert updated["value"] == update_data["value"]
    assert updated["updated_at"] != original["updated_at"]

@pytest.mark.asyncio
async def test_delete_memory(client: AsyncClient, test_subtenant: Dict):
    """Test deleting a memory."""
    # Create a memory first
    memory_data = {
        "key": "delete_test_key",
        "value": "To be deleted"
    }
    
    create_response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json=memory_data
    )
    assert create_response.status_code == 200
    
    # Delete the memory
    delete_response = await client.delete(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_data['key']}"
    )
    assert delete_response.status_code == 200
    
    # Try to get the deleted memory - should return 404
    get_response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_data['key']}"
    )
    assert get_response.status_code == 404

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_memory_operations_invalid_subtenant(client: AsyncClient):
    """Test memory operations with invalid subtenant ID."""
    fake_subtenant_id = str(uuid4())
    
    # Test create
    create_response = await client.post(
        f"/api/v1/subtenants/{fake_subtenant_id}/memories",
        json={"key": "test", "value": "test"}
    )
    assert create_response.status_code == 404
    
    # Test list
    list_response = await client.get(f"/api/v1/subtenants/{fake_subtenant_id}/memories")
    assert list_response.status_code == 404
    
    # Test get
    get_response = await client.get(f"/api/v1/subtenants/{fake_subtenant_id}/memories/test")
    assert get_response.status_code == 404
    
    # Test update
    update_response = await client.put(
        f"/api/v1/subtenants/{fake_subtenant_id}/memories/test",
        json={"value": "updated"}
    )
    assert update_response.status_code == 404
    
    # Test delete
    delete_response = await client.delete(f"/api/v1/subtenants/{fake_subtenant_id}/memories/test")
    assert delete_response.status_code == 404

@pytest.mark.asyncio
async def test_get_nonexistent_memory(client: AsyncClient, test_subtenant: Dict):
    """Test getting a memory that doesn't exist."""
    response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/nonexistent_key"
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_nonexistent_memory(client: AsyncClient, test_subtenant: Dict):
    """Test updating a memory that doesn't exist."""
    response = await client.put(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/nonexistent_key",
        json={"value": "new value"}
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_nonexistent_memory(client: AsyncClient, test_subtenant: Dict):
    """Test deleting a memory that doesn't exist."""
    response = await client.delete(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/nonexistent_key"
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_invalid_memory_data(client: AsyncClient, test_subtenant: Dict):
    """Test creating memory with invalid data."""
    # Missing key
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json={"value": "No key provided"}
    )
    assert response.status_code == 422
    
    # Missing value
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json={"key": "no_value"}
    )
    assert response.status_code == 422
    
    # Empty key
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json={"key": "", "value": "Empty key"}
    )
    # Might succeed or fail depending on validation
    assert response.status_code in [200, 400, 422]

@pytest.mark.asyncio
async def test_invalid_uuid_format(client: AsyncClient):
    """Test memory operations with invalid UUID format."""
    invalid_uuid = "not-a-uuid"
    
    # Test create
    response = await client.post(
        f"/api/v1/subtenants/{invalid_uuid}/memories",
        json={"key": "test", "value": "test"}
    )
    assert response.status_code == 422
    
    # Test list
    response = await client.get(f"/api/v1/subtenants/{invalid_uuid}/memories")
    assert response.status_code == 422
    
    # Test get
    response = await client.get(f"/api/v1/subtenants/{invalid_uuid}/memories/test")
    assert response.status_code == 422
    
    # Test update
    response = await client.put(
        f"/api/v1/subtenants/{invalid_uuid}/memories/test",
        json={"value": "updated"}
    )
    assert response.status_code == 422
    
    # Test delete
    response = await client.delete(f"/api/v1/subtenants/{invalid_uuid}/memories/test")
    assert response.status_code == 422

# ============================================================================
# MEMORY ISOLATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_memory_isolation_between_subtenants(client: AsyncClient, test_subtenant: Dict, second_subtenant: Dict):
    """Test that memories are isolated between different subtenants."""
    memory_data = {
        "key": "isolation_test",
        "value": "This memory belongs to subtenant 1"
    }
    
    # Create memory for first subtenant
    create_response1 = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json=memory_data
    )
    assert create_response1.status_code == 200
    
    # Try to get the memory from second subtenant - should not exist
    get_response = await client.get(
        f"/api/v1/subtenants/{second_subtenant['id']}/memories/{memory_data['key']}"
    )
    assert get_response.status_code == 404
    
    # Create memory with same key for second subtenant
    second_memory_data = {
        "key": "isolation_test",
        "value": "This memory belongs to subtenant 2"
    }
    
    create_response2 = await client.post(
        f"/api/v1/subtenants/{second_subtenant['id']}/memories",
        json=second_memory_data
    )
    assert create_response2.status_code == 200
    
    # Verify both subtenants have their own memory with same key
    get_response1 = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_data['key']}"
    )
    assert get_response1.status_code == 200
    memory1 = get_response1.json()
    assert memory1["value"] == memory_data["value"]
    
    get_response2 = await client.get(
        f"/api/v1/subtenants/{second_subtenant['id']}/memories/{memory_data['key']}"
    )
    assert get_response2.status_code == 200
    memory2 = get_response2.json()
    assert memory2["value"] == second_memory_data["value"]

@pytest.mark.asyncio
async def test_memory_lists_are_isolated(client: AsyncClient, test_subtenant: Dict, second_subtenant: Dict):
    """Test that memory lists are isolated between subtenants."""
    # Create memories for first subtenant
    subtenant1_memories = [
        {"key": "st1_mem1", "value": "Subtenant 1 Memory 1"},
        {"key": "st1_mem2", "value": "Subtenant 1 Memory 2"}
    ]
    
    for memory in subtenant1_memories:
        await client.post(
            f"/api/v1/subtenants/{test_subtenant['id']}/memories",
            json=memory
        )
    
    # Create memories for second subtenant
    subtenant2_memories = [
        {"key": "st2_mem1", "value": "Subtenant 2 Memory 1"},
        {"key": "st2_mem2", "value": "Subtenant 2 Memory 2"}
    ]
    
    for memory in subtenant2_memories:
        await client.post(
            f"/api/v1/subtenants/{second_subtenant['id']}/memories",
            json=memory
        )
    
    # Get memory lists for both subtenants
    list1_response = await client.get(f"/api/v1/subtenants/{test_subtenant['id']}/memories")
    assert list1_response.status_code == 200
    list1 = list1_response.json()
    
    list2_response = await client.get(f"/api/v1/subtenants/{second_subtenant['id']}/memories")
    assert list2_response.status_code == 200
    list2 = list2_response.json()
    
    # Verify each list contains only its own memories
    list1_keys = [m["key"] for m in list1]
    list2_keys = [m["key"] for m in list2]
    
    for memory in subtenant1_memories:
        assert memory["key"] in list1_keys
        assert memory["key"] not in list2_keys
    
    for memory in subtenant2_memories:
        assert memory["key"] in list2_keys
        assert memory["key"] not in list1_keys

# ============================================================================
# PAGINATION AND FILTERING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_memory_list_pagination(client: AsyncClient, test_subtenant: Dict):
    """Test pagination for memory listing."""
    # Create multiple memories
    base_memories = []
    for i in range(5):
        memory_data = {
            "key": f"pagination_test_{i}",
            "value": f"Pagination test value {i}"
        }
        response = await client.post(
            f"/api/v1/subtenants/{test_subtenant['id']}/memories",
            json=memory_data
        )
        if response.status_code == 200:
            base_memories.append(memory_data)
    
    # Test with limit
    limit_response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories?limit=2"
    )
    assert limit_response.status_code == 200
    limited_memories = limit_response.json()
    assert len(limited_memories) <= 2
    
    # Test with skip
    skip_response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories?skip=1"
    )
    assert skip_response.status_code == 200
    
    # Test with both skip and limit
    paginated_response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories?skip=1&limit=2"
    )
    assert paginated_response.status_code == 200
    paginated_memories = paginated_response.json()
    assert len(paginated_memories) <= 2

@pytest.mark.asyncio
async def test_memory_list_invalid_parameters(client: AsyncClient, test_subtenant: Dict):
    """Test memory listing with invalid parameters."""
    # Test with negative skip
    response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories?skip=-1"
    )
    # Should work or return validation error
    assert response.status_code in [200, 422]
    
    # Test with negative limit
    response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories?limit=-1"
    )
    # Should work or return validation error
    assert response.status_code in [200, 422]
    
    # Test with non-integer parameters
    response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories?skip=abc"
    )
    assert response.status_code == 422
    
    response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories?limit=xyz"
    )
    assert response.status_code == 422

# ============================================================================
# MEMORY CONTENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_large_memory_value(client: AsyncClient, test_subtenant: Dict):
    """Test storing large memory values."""
    large_value = "A" * 10000  # 10KB of text
    
    memory_data = {
        "key": "large_memory_test",
        "value": large_value
    }
    
    response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json=memory_data
    )
    assert response.status_code == 200
    
    created = response.json()
    assert created["value"] == large_value
    
    # Verify we can retrieve it
    get_response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_data['key']}"
    )
    assert get_response.status_code == 200
    retrieved = get_response.json()
    assert retrieved["value"] == large_value

@pytest.mark.asyncio
async def test_special_characters_in_memory(client: AsyncClient, test_subtenant: Dict):
    """Test storing memory values with special characters."""
    special_values = [
        "Hello, 世界! 🌍",
        '{"json": "value", "number": 123}',
        "Line 1\nLine 2\nLine 3",
        "Emoji test: 😀🎉🚀💯",
        "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
    ]
    
    for i, value in enumerate(special_values):
        memory_data = {
            "key": f"special_chars_test_{i}",
            "value": value
        }
        
        response = await client.post(
            f"/api/v1/subtenants/{test_subtenant['id']}/memories",
            json=memory_data
        )
        assert response.status_code == 200
        
        created = response.json()
        assert created["value"] == value
        
        # Verify retrieval
        get_response = await client.get(
            f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_data['key']}"
        )
        assert get_response.status_code == 200
        retrieved = get_response.json()
        assert retrieved["value"] == value

@pytest.mark.asyncio
async def test_memory_key_restrictions(client: AsyncClient, test_subtenant: Dict):
    """Test memory key format restrictions."""
    test_keys = [
        "normal_key",
        "key-with-dashes",
        "key_with_underscores",
        "key123",
        "UPPERCASE_KEY",
        "mixedCaseKey",
        "key.with.dots",
        "key with spaces",  # Might not be allowed
        "key/with/slashes",  # Might not be allowed
        "",  # Empty key - should fail
        "very_long_key_" + "a" * 200  # Very long key
    ]
    
    for i, key in enumerate(test_keys):
        memory_data = {
            "key": key,
            "value": f"Test value for key: {key}"
        }
        
        response = await client.post(
            f"/api/v1/subtenants/{test_subtenant['id']}/memories",
            json=memory_data
        )
        
        # Some keys might be rejected, others accepted
        if key == "" or len(key) > 255:
            # Empty keys and very long keys should be rejected
            assert response.status_code in [400, 422]
        else:
            # Other keys might be accepted or rejected depending on validation rules
            assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            # If accepted, verify it can be retrieved
            get_response = await client.get(
                f"/api/v1/subtenants/{test_subtenant['id']}/memories/{key}"
            )
            assert get_response.status_code == 200

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_memory_lifecycle(client: AsyncClient, test_subtenant: Dict):
    """Test the complete lifecycle of a memory."""
    memory_key = "lifecycle_test_key"
    
    # Step 1: Create memory
    create_data = {
        "key": memory_key,
        "value": "Initial value"
    }
    create_response = await client.post(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories",
        json=create_data
    )
    assert create_response.status_code == 200
    
    # Step 2: Verify it appears in list
    list_response = await client.get(f"/api/v1/subtenants/{test_subtenant['id']}/memories")
    assert list_response.status_code == 200
    memories = list_response.json()
    memory_keys = [m["key"] for m in memories]
    assert memory_key in memory_keys
    
    # Step 3: Get individual memory
    get_response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_key}"
    )
    assert get_response.status_code == 200
    retrieved = get_response.json()
    assert retrieved["key"] == memory_key
    assert retrieved["value"] == create_data["value"]
    
    # Step 4: Update memory
    update_data = {"value": "Updated value"}
    update_response = await client.put(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_key}",
        json=update_data
    )
    assert update_response.status_code == 200
    
    # Step 5: Verify update
    get_updated_response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_key}"
    )
    assert get_updated_response.status_code == 200
    updated = get_updated_response.json()
    assert updated["value"] == update_data["value"]
    
    # Step 6: Delete memory
    delete_response = await client.delete(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_key}"
    )
    assert delete_response.status_code == 200
    
    # Step 7: Verify it's gone
    get_after_delete_response = await client.get(
        f"/api/v1/subtenants/{test_subtenant['id']}/memories/{memory_key}"
    )
    assert get_after_delete_response.status_code == 404

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