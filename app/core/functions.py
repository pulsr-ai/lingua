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
        return self._functions.get(name)
    
    def get_definitions(self) -> List[Dict[str, Any]]:
        """Get all function definitions in OpenAI tools format"""
        return list(self._definitions.values())
    
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
            raise ValueError(f"Function '{name}' not found")
        
        return await handler.execute(**arguments)


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


# Example built-in functions
class GetCurrentTimeFunction(BaseFunctionHandler):
    async def execute(self, **kwargs) -> str:
        from datetime import datetime
        format = kwargs.get("format", "%Y-%m-%d %H:%M:%S")
        return datetime.now().strftime(format)
    
    def get_definition(self) -> FunctionDefinition:
        return FunctionDefinition(
            name="get_current_time",
            description="Get the current date and time",
            parameters=[
                FunctionParameter(
                    name="format",
                    type="string",
                    description="The format string for the date/time (default: %Y-%m-%d %H:%M:%S)",
                    required=False
                )
            ]
        )


class CalculatorFunction(BaseFunctionHandler):
    async def execute(self, expression: str) -> float:
        # Simple safe evaluation for basic math
        allowed_chars = "0123456789+-*/()., "
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Invalid characters in expression")
        
        try:
            result = eval(expression)
            return float(result)
        except Exception as e:
            raise ValueError(f"Failed to evaluate expression: {str(e)}")
    
    def get_definition(self) -> FunctionDefinition:
        return FunctionDefinition(
            name="calculator",
            description="Perform basic mathematical calculations",
            parameters=[
                FunctionParameter(
                    name="expression",
                    type="string",
                    description="The mathematical expression to evaluate (e.g., '2 + 2 * 3')"
                )
            ]
        )


# Register built-in functions
function_registry.register(GetCurrentTimeFunction())
function_registry.register(CalculatorFunction())