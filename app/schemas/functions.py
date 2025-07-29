from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.functions import FunctionParameter


class FunctionDefinitionResponse(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class RegisterFunctionRequest(BaseModel):
    name: str
    description: str
    parameters: List[FunctionParameter]
    code: str  # Python code for the function


class ExecuteFunctionRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ExecuteFunctionResponse(BaseModel):
    result: Any