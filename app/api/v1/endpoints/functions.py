from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.functions import function_registry, create_function_handler
from app.db.base import get_db
from app.db.models import RegisteredFunction
from app.schemas.functions import (
    FunctionDefinitionResponse,
    RegisterFunctionRequest,
    ExecuteFunctionRequest,
    ExecuteFunctionResponse,
    RegisteredFunctionResponse,
    UpdateFunctionRequest
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


@router.post("/functions/register", response_model=RegisteredFunctionResponse)
def register_function(request: RegisterFunctionRequest, db: Session = Depends(get_db)):
    """Register a new function dynamically"""
    try:
        # Test the code by executing it
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
        
        # Convert parameters to the format expected by the database
        parameters_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in request.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            
            parameters_schema["properties"][param.name] = prop
            if param.required:
                parameters_schema["required"].append(param.name)
        
        # Save to database
        db_function = RegisteredFunction(
            name=request.name,
            description=request.description,
            parameters=parameters_schema,
            code=request.code
        )
        db.add(db_function)
        db.commit()
        db.refresh(db_function)
        
        # Clear the function registry cache so it reloads from database
        function_registry.reload_db_functions()
        
        return db_function
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/functions/registered", response_model=List[RegisteredFunctionResponse])
def list_registered_functions(db: Session = Depends(get_db)):
    """List all registered functions from database"""
    functions = db.query(RegisteredFunction).all()
    return functions


@router.get("/functions/registered/{function_id}", response_model=RegisteredFunctionResponse)
def get_registered_function(function_id: UUID, db: Session = Depends(get_db)):
    """Get a specific registered function"""
    function = db.query(RegisteredFunction).filter(RegisteredFunction.id == function_id).first()
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    return function


@router.put("/functions/registered/{function_id}", response_model=RegisteredFunctionResponse)
def update_registered_function(
    function_id: UUID, 
    request: UpdateFunctionRequest, 
    db: Session = Depends(get_db)
):
    """Update a registered function"""
    function = db.query(RegisteredFunction).filter(RegisteredFunction.id == function_id).first()
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    
    try:
        # Update fields
        if request.description is not None:
            function.description = request.description
        
        if request.code is not None:
            # Test the new code
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
            
            function.code = request.code
        
        if request.parameters is not None:
            # Convert parameters to schema format
            parameters_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            for param in request.parameters:
                prop = {
                    "type": param.type,
                    "description": param.description
                }
                if param.enum:
                    prop["enum"] = param.enum
                
                parameters_schema["properties"][param.name] = prop
                if param.required:
                    parameters_schema["required"].append(param.name)
            
            function.parameters = parameters_schema
        
        if request.is_active is not None:
            function.is_active = request.is_active
        
        db.commit()
        db.refresh(function)
        
        # Clear cache
        function_registry.reload_db_functions()
        
        return function
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/functions/registered/{function_id}")
def delete_registered_function(function_id: UUID, db: Session = Depends(get_db)):
    """Delete a registered function"""
    function = db.query(RegisteredFunction).filter(RegisteredFunction.id == function_id).first()
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    
    db.delete(function)
    db.commit()
    
    # Clear cache
    function_registry.reload_db_functions()
    
    return {"message": f"Function '{function.name}' deleted successfully"}


@router.delete("/functions/{name}")
def unregister_function(name: str):
    """Unregister a built-in function (not database functions)"""
    try:
        function_registry.unregister(name)
        return {"message": f"Function '{name}' unregistered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))