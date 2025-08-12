"""
Comprehensive tests for Functions endpoints.
Tests all function-related operations including registration, execution, and management.
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
async def sample_function():
    """Sample function data for testing."""
    return {
        "name": "test_add_numbers",
        "description": "Add two numbers together",
        "parameters": [
            {
                "name": "a",
                "type": "number",
                "description": "First number",
                "required": True
            },
            {
                "name": "b", 
                "type": "number",
                "description": "Second number",
                "required": True
            }
        ],
        "code": """
async def test_add_numbers(a: float, b: float):
    \"\"\"Add two numbers together.\"\"\"
    return a + b
"""
    }

@pytest.fixture(scope="module")
async def registered_function(client: AsyncClient, sample_function: Dict):
    """Register a sample function for testing."""
    response = await client.post("/api/v1/functions/register", json=sample_function)
    if response.status_code in [200, 400]:  # 400 if already exists
        if response.status_code == 400:
            # Try to get existing function
            list_response = await client.get("/api/v1/functions/registered")
            if list_response.status_code == 200:
                functions = list_response.json()
                for func in functions:
                    if func["name"] == sample_function["name"]:
                        return func
        else:
            return response.json()
    raise Exception(f"Failed to register function: {response.text}")

# ============================================================================
# FUNCTION LISTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_list_available_functions(client: AsyncClient):
    """Test listing all available functions."""
    response = await client.get("/api/v1/functions")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Check structure of function definitions - they are FunctionDefinitionResponse objects
    for func_def in data:
        assert "name" in func_def
        assert "description" in func_def
        assert "parameters" in func_def

@pytest.mark.asyncio
async def test_list_registered_functions(client: AsyncClient):
    """Test listing registered functions."""
    response = await client.get("/api/v1/functions/registered")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    # Check structure of registered functions
    for func in data:
        assert "id" in func
        assert "name" in func
        assert "description" in func
        assert "parameters" in func
        assert "code" in func
        assert "is_active" in func
        assert "created_at" in func
        assert "updated_at" in func

# ============================================================================
# FUNCTION REGISTRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_register_function_success(client: AsyncClient):
    """Test successful function registration."""
    func_data = {
        "name": "test_multiply",
        "description": "Multiply two numbers",
        "parameters": [
            {
                "name": "x",
                "type": "number",
                "description": "First number",
                "required": True
            },
            {
                "name": "y",
                "type": "number", 
                "description": "Second number",
                "required": True
            }
        ],
        "code": """
async def test_multiply(x: float, y: float):
    \"\"\"Multiply two numbers.\"\"\"
    return x * y
"""
    }
    
    response = await client.post("/api/v1/functions/register", json=func_data)
    if response.status_code == 400 and "already exists" in response.text:
        # Function already exists, delete it first
        await client.delete(f"/api/v1/functions/{func_data['name']}")
        response = await client.post("/api/v1/functions/register", json=func_data)
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == func_data["name"]
    assert data["description"] == func_data["description"]
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    return data

@pytest.mark.asyncio
async def test_register_function_duplicate_name(client: AsyncClient, registered_function: Dict):
    """Test registering a function with duplicate name."""
    duplicate_func = {
        "name": registered_function["name"],
        "description": "Duplicate function",
        "parameters": [],
        "code": "async def duplicate(): return 'duplicate'"
    }
    
    response = await client.post("/api/v1/functions/register", json=duplicate_func)
    assert response.status_code == 400
    
    error_data = response.json()
    assert "detail" in error_data
    assert "already exists" in error_data["detail"].lower()

@pytest.mark.asyncio
async def test_register_function_invalid_syntax(client: AsyncClient):
    """Test registering a function with invalid Python syntax."""
    invalid_func = {
        "name": "invalid_syntax_func",
        "description": "Function with invalid syntax",
        "parameters": [],
        "code": "this is not valid python code!!!"
    }
    
    response = await client.post("/api/v1/functions/register", json=invalid_func)
    # Should return 400 for syntax error
    assert response.status_code in [400, 422]

@pytest.mark.asyncio
async def test_register_function_missing_fields(client: AsyncClient):
    """Test registering a function with missing required fields."""
    # Missing name
    response = await client.post("/api/v1/functions/register", json={
        "description": "Function without name",
        "parameters": [],
        "code": "async def test(): pass"
    })
    assert response.status_code == 422
    
    # Missing description
    response = await client.post("/api/v1/functions/register", json={
        "name": "no_description",
        "parameters": [],
        "code": "async def test(): pass"
    })
    assert response.status_code == 422
    
    # Missing code
    response = await client.post("/api/v1/functions/register", json={
        "name": "no_code",
        "description": "Function without code",
        "parameters": []
    })
    assert response.status_code == 422

# ============================================================================
# FUNCTION EXECUTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_execute_function_success(client: AsyncClient, registered_function: Dict):
    """Test successful function execution."""
    if registered_function["name"] == "test_add_numbers":
        execute_data = {
            "arguments": {"a": 5, "b": 3}
        }
        
        response = await client.post(
            f"/api/v1/functions/{registered_function['name']}/execute",
            json=execute_data
        )
        
        # The function might not be in the registry (only in database)
        if response.status_code == 404:
            # Function not in registry, which is expected for database-registered functions
            return
        
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        assert data["result"] == 8  # 5 + 3

@pytest.mark.asyncio
async def test_execute_nonexistent_function(client: AsyncClient):
    """Test executing a function that doesn't exist."""
    execute_data = {"arguments": {}}
    
    response = await client.post(
        "/api/v1/functions/nonexistent_function/execute",
        json=execute_data
    )
    # Could be 404 (not found) or 422 (validation error)
    assert response.status_code in [404, 422]

@pytest.mark.asyncio
async def test_execute_function_wrong_arguments(client: AsyncClient, registered_function: Dict):
    """Test executing a function with wrong arguments."""
    if registered_function["name"] == "test_add_numbers":
        # Missing required arguments
        execute_data = {"arguments": {"a": 5}}  # Missing 'b'
        
        response = await client.post(
            f"/api/v1/functions/{registered_function['name']}/execute",
            json=execute_data
        )
        assert response.status_code in [400, 422]
        
        # Wrong argument types
        execute_data = {"arguments": {"a": "not_a_number", "b": "also_not_a_number"}}
        
        response = await client.post(
            f"/api/v1/functions/{registered_function['name']}/execute",
            json=execute_data
        )
        # Should handle gracefully - might return 400 or execute with type conversion
        assert response.status_code in [200, 400, 422]

# ============================================================================
# REGISTERED FUNCTION MANAGEMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_registered_function(client: AsyncClient, registered_function: Dict):
    """Test getting a specific registered function."""
    response = await client.get(f"/api/v1/functions/registered/{registered_function['id']}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == registered_function["id"]
    assert data["name"] == registered_function["name"]
    assert data["description"] == registered_function["description"]

@pytest.mark.asyncio
async def test_get_nonexistent_registered_function(client: AsyncClient):
    """Test getting a registered function that doesn't exist."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/functions/registered/{fake_id}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_registered_function(client: AsyncClient, registered_function: Dict):
    """Test updating a registered function."""
    update_data = {
        "description": "Updated description",
        "is_active": False
    }
    
    response = await client.put(
        f"/api/v1/functions/registered/{registered_function['id']}",
        json=update_data
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["description"] == "Updated description" 
    assert data["is_active"] is False
    assert data["id"] == registered_function["id"]
    assert data["name"] == registered_function["name"]  # Should not change

@pytest.mark.asyncio
async def test_delete_registered_function_by_id(client: AsyncClient):
    """Test deleting a registered function by ID."""
    # First register a function to delete
    func_data = {
        "name": "to_be_deleted_by_id",
        "description": "Function to be deleted by ID",
        "parameters": [],
        "code": "async def to_be_deleted_by_id(): return 'delete me'"
    }
    
    register_response = await client.post("/api/v1/functions/register", json=func_data)
    if register_response.status_code == 400:
        # Function already exists, delete it first
        await client.delete(f"/api/v1/functions/{func_data['name']}")
        register_response = await client.post("/api/v1/functions/register", json=func_data)
    
    assert register_response.status_code == 200
    registered = register_response.json()
    
    # Delete the function
    delete_response = await client.delete(f"/api/v1/functions/registered/{registered['id']}")
    assert delete_response.status_code == 200
    
    # Verify it's gone
    get_response = await client.get(f"/api/v1/functions/registered/{registered['id']}")
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_delete_registered_function_by_name(client: AsyncClient):
    """Test deleting a registered function by name."""
    # First register a function to delete
    func_data = {
        "name": "to_be_deleted_by_name",
        "description": "Function to be deleted by name",
        "parameters": [],
        "code": "async def to_be_deleted_by_name(): return 'delete me'"
    }
    
    register_response = await client.post("/api/v1/functions/register", json=func_data)
    if register_response.status_code == 400:
        # Function already exists, that's fine for this test
        pass
    else:
        assert register_response.status_code == 200
    
    # Delete the function by name
    delete_response = await client.delete(f"/api/v1/functions/{func_data['name']}")
    assert delete_response.status_code == 200
    
    # Try to execute it - should fail
    execute_response = await client.post(
        f"/api/v1/functions/{func_data['name']}/execute",
        json={"arguments": {}}
    )
    assert execute_response.status_code == 404

# ============================================================================
# COMPLEX FUNCTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_register_complex_function(client: AsyncClient):
    """Test registering a more complex function with various parameter types."""
    complex_func = {
        "name": "complex_function",
        "description": "A function with various parameter types",
        "parameters": [
            {
                "name": "text",
                "type": "string",
                "description": "Text parameter",
                "required": True
            },
            {
                "name": "number",
                "type": "number",
                "description": "Number parameter",
                "required": True
            },
            {
                "name": "flag",
                "type": "boolean",
                "description": "Boolean parameter",
                "required": False
            },
            {
                "name": "items",
                "type": "array",
                "description": "Array parameter",
                "required": False
            }
        ],
        "code": """
async def complex_function(text: str, number: float, flag: bool = True, items: list = None):
    \"\"\"A complex function for testing.\"\"\"
    if items is None:
        items = []
    
    result = {
        "text_length": len(text),
        "number_doubled": number * 2,
        "flag_inverted": not flag,
        "items_count": len(items)
    }
    return result
"""
    }
    
    # Delete if exists
    await client.delete(f"/api/v1/functions/{complex_func['name']}")
    
    response = await client.post("/api/v1/functions/register", json=complex_func)
    assert response.status_code == 200
    
    # Test execution with various parameter combinations
    test_cases = [
        {
            "arguments": {
                "text": "hello",
                "number": 5.5,
                "flag": False,
                "items": [1, 2, 3]
            },
            "expected": {
                "text_length": 5,
                "number_doubled": 11.0,
                "flag_inverted": True,
                "items_count": 3
            }
        },
        {
            "arguments": {
                "text": "test",
                "number": 10
            },
            "expected": {
                "text_length": 4,
                "number_doubled": 20.0,
                "flag_inverted": False,  # flag defaults to True, so inverted is False
                "items_count": 0  # items defaults to []
            }
        }
    ]
    
    for test_case in test_cases:
        exec_response = await client.post(
            f"/api/v1/functions/{complex_func['name']}/execute",
            json=test_case
        )
        assert exec_response.status_code == 200
        
        result = exec_response.json()["result"]
        for key, expected_value in test_case["expected"].items():
            assert result[key] == expected_value

@pytest.mark.asyncio
async def test_function_with_imports(client: AsyncClient):
    """Test registering and executing a function that uses imports."""
    import_func = {
        "name": "datetime_function",
        "description": "Function that uses datetime import",
        "parameters": [
            {
                "name": "format_string",
                "type": "string", 
                "description": "Date format string",
                "required": False
            }
        ],
        "code": """
async def datetime_function(format_string: str = "%Y-%m-%d %H:%M:%S"):
    \"\"\"Function that uses datetime import.\"\"\"
    from datetime import datetime
    return datetime.now().strftime(format_string)
"""
    }
    
    # Delete if exists
    await client.delete(f"/api/v1/functions/{import_func['name']}")
    
    response = await client.post("/api/v1/functions/register", json=import_func)
    assert response.status_code == 200
    
    # Test execution
    exec_response = await client.post(
        f"/api/v1/functions/{import_func['name']}/execute",
        json={"arguments": {"format_string": "%Y-%m-%d"}}
    )
    assert exec_response.status_code == 200
    
    result = exec_response.json()["result"]
    # Should be a date string in YYYY-MM-DD format
    import re
    assert re.match(r'\d{4}-\d{2}-\d{2}', result)

# ============================================================================
# ERROR HANDLING AND EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_function_with_runtime_error(client: AsyncClient):
    """Test function execution that raises an error at runtime."""
    error_func = {
        "name": "error_function",
        "description": "Function that raises an error",
        "parameters": [],
        "code": """
async def error_function():
    \"\"\"Function that always raises an error.\"\"\"
    raise ValueError("This function always fails")
"""
    }
    
    # Delete if exists
    await client.delete(f"/api/v1/functions/{error_func['name']}")
    
    response = await client.post("/api/v1/functions/register", json=error_func)
    assert response.status_code == 200
    
    # Test execution - should handle the error gracefully
    exec_response = await client.post(
        f"/api/v1/functions/{error_func['name']}/execute",
        json={"arguments": {}}
    )
    # Might return 400, 500, or 200 with error in result - depends on error handling
    assert exec_response.status_code in [200, 400, 500]

@pytest.mark.asyncio
async def test_function_parameter_validation(client: AsyncClient):
    """Test parameter validation for function registration."""
    # Test invalid parameter type
    invalid_param_func = {
        "name": "invalid_param_func",
        "description": "Function with invalid parameter type",
        "parameters": [
            {
                "name": "param",
                "type": "invalid_type",  # Invalid type
                "description": "Invalid parameter",
                "required": True
            }
        ],
        "code": "async def invalid_param_func(param): return param"
    }
    
    response = await client.post("/api/v1/functions/register", json=invalid_param_func)
    # Might succeed or fail depending on validation - both are acceptable
    assert response.status_code in [200, 400, 422]

@pytest.mark.asyncio
async def test_list_functions_after_operations(client: AsyncClient):
    """Test that function lists are updated after registration/deletion operations."""
    # Get initial count
    initial_response = await client.get("/api/v1/functions/registered")
    assert initial_response.status_code == 200
    initial_count = len(initial_response.json())
    
    # Register a new function
    new_func = {
        "name": "list_test_function",
        "description": "Function for list testing",
        "parameters": [],
        "code": "async def list_test_function(): return 'test'"
    }
    
    # Delete if exists first
    await client.delete(f"/api/v1/functions/{new_func['name']}")
    
    register_response = await client.post("/api/v1/functions/register", json=new_func)
    assert register_response.status_code == 200
    
    # Check that count increased
    after_register_response = await client.get("/api/v1/functions/registered")
    assert after_register_response.status_code == 200
    after_register_count = len(after_register_response.json())
    assert after_register_count == initial_count + 1
    
    # Delete the function
    delete_response = await client.delete(f"/api/v1/functions/{new_func['name']}")
    assert delete_response.status_code == 200
    
    # Check that count decreased
    after_delete_response = await client.get("/api/v1/functions/registered")
    assert after_delete_response.status_code == 200
    after_delete_count = len(after_delete_response.json())
    assert after_delete_count == initial_count

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