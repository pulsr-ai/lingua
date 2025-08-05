from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
import json
import inspect
from pydantic import BaseModel


class FunctionParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[Any]] = None


class FunctionDefinition(BaseModel):
    name: str
    description: str
    parameters: List[FunctionParameter]


class BaseFunctionHandler(ABC):
    """Base class for function handlers"""
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the function with given parameters"""
        pass
    
    @abstractmethod
    def get_definition(self) -> FunctionDefinition:
        """Get the function definition for LLM"""
        pass


class FunctionRegistry:
    """Registry for managing available functions"""
    
    def __init__(self):
        self._functions: Dict[str, BaseFunctionHandler] = {}
        self._definitions: Dict[str, Dict[str, Any]] = {}
        self._db_functions: Dict[str, BaseFunctionHandler] = {}  # Database stored functions
    
    def register(self, handler: BaseFunctionHandler):
        """Register a function handler"""
        definition = handler.get_definition()
        self._functions[definition.name] = handler
        
        # Convert to OpenAI tools format (newer)
        tool_def = {
            "type": "function",
            "function": {
                "name": definition.name,
                "description": definition.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        for param in definition.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            
            tool_def["function"]["parameters"]["properties"][param.name] = prop
            if param.required:
                tool_def["function"]["parameters"]["required"].append(param.name)
        
        self._definitions[definition.name] = tool_def
    
    def unregister(self, name: str):
        """Unregister a function"""
        if name in self._functions:
            del self._functions[name]
            del self._definitions[name]
    
    def get_function(self, name: str) -> Optional[BaseFunctionHandler]:
        """Get a function handler by name"""
        # Check built-in functions first
        if name in self._functions:
            return self._functions[name]
        # Then check database functions
        return self._db_functions.get(name)
    
    def get_definitions(self) -> List[Dict[str, Any]]:
        """Get all function definitions in OpenAI tools format"""
        all_definitions = list(self._definitions.values())
        # Add database function definitions
        from app.db.base import SessionLocal
        from app.db.models import RegisteredFunction
        
        db = SessionLocal()
        try:
            db_functions = db.query(RegisteredFunction).filter(RegisteredFunction.is_active == True).all()
            for func in db_functions:
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": func.name,
                        "description": func.description,
                        "parameters": func.parameters
                    }
                }
                all_definitions.append(tool_def)
        finally:
            db.close()
        
        return all_definitions
    
    def get_functions_format(self) -> List[Dict[str, Any]]:
        """Get all function definitions in legacy OpenAI functions format"""
        functions = []
        for tool_def in self._definitions.values():
            if tool_def["type"] == "function":
                functions.append(tool_def["function"])
        return functions
    
    def get_definition(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific function definition"""
        return self._definitions.get(name)
    
    async def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function by name with arguments"""
        handler = self.get_function(name)
        if not handler:
            # Try to load from database
            await self._load_db_function(name)
            handler = self.get_function(name)
            if not handler:
                raise ValueError(f"Function '{name}' not found")
        
        return await handler.execute(**arguments)
    
    async def _load_db_function(self, name: str):
        """Load a function from database"""
        from app.db.base import SessionLocal
        from app.db.models import RegisteredFunction
        
        db = SessionLocal()
        try:
            func = db.query(RegisteredFunction).filter(
                RegisteredFunction.name == name,
                RegisteredFunction.is_active == True
            ).first()
            
            if func:
                # Create function handler from database record
                namespace = {}
                exec(func.code, namespace)
                
                # Find the function in the namespace
                python_func = None
                for obj_name, obj in namespace.items():
                    if callable(obj) and not obj_name.startswith('_'):
                        python_func = obj
                        break
                
                if python_func:
                    # Convert parameters back to FunctionParameter objects
                    parameters = []
                    if func.parameters.get("properties"):
                        for param_name, param_def in func.parameters["properties"].items():
                            param = FunctionParameter(
                                name=param_name,
                                type=param_def.get("type", "string"),
                                description=param_def.get("description", ""),
                                required=param_name in func.parameters.get("required", []),
                                enum=param_def.get("enum")
                            )
                            parameters.append(param)
                    
                    handler = create_function_handler(python_func, func.name, func.description, parameters)
                    self._db_functions[name] = handler
        finally:
            db.close()
    
    def reload_db_functions(self):
        """Reload all database functions"""
        self._db_functions.clear()
        # Functions will be loaded on-demand


# Global function registry
function_registry = FunctionRegistry()


def create_function_handler(func: Callable, name: str, description: str, 
                          parameters: List[FunctionParameter]) -> BaseFunctionHandler:
    """Create a function handler from a regular function"""
    
    class DynamicFunctionHandler(BaseFunctionHandler):
        async def execute(self, **kwargs) -> Any:
            if inspect.iscoroutinefunction(func):
                return await func(**kwargs)
            else:
                return func(**kwargs)
        
        def get_definition(self) -> FunctionDefinition:
            return FunctionDefinition(
                name=name,
                description=description,
                parameters=parameters
            )
    
    return DynamicFunctionHandler()