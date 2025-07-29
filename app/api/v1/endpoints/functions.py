from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from app.core.functions import function_registry, create_function_handler
from app.schemas.functions import (
    FunctionDefinitionResponse,
    RegisterFunctionRequest,
    ExecuteFunctionRequest,
    ExecuteFunctionResponse
)


router = APIRouter()


@router.get("/functions", response_model=List[FunctionDefinitionResponse])
def list_functions():
    """List all available functions"""
    definitions = function_registry.get_definitions()
    return [
        FunctionDefinitionResponse(
            name=def_dict["name"],
            description=def_dict["description"],
            parameters=def_dict["parameters"]
        )
        for def_dict in definitions
    ]


@router.post("/functions/{name}/execute", response_model=ExecuteFunctionResponse)
async def execute_function(name: str, request: ExecuteFunctionRequest):
    """Execute a function by name"""
    try:
        result = await function_registry.execute(name, request.arguments)
        return ExecuteFunctionResponse(result=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/functions/register")
def register_function(request: RegisterFunctionRequest):
    """Register a new function dynamically"""
    try:
        # Create a function from the provided code
        namespace = {}
        exec(request.code, namespace)
        
        # Find the function in the namespace
        func = None
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith('_'):
                func = obj
                break
        
        if not func:
            raise ValueError("No callable function found in the provided code")
        
        # Create and register the handler
        handler = create_function_handler(func, request.name, request.description, request.parameters)
        function_registry.register(handler)
        
        return {"message": f"Function '{request.name}' registered successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/functions/{name}")
def unregister_function(name: str):
    """Unregister a function"""
    try:
        function_registry.unregister(name)
        return {"message": f"Function '{name}' unregistered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))