from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID

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


class RegisteredFunctionResponse(BaseModel):
    id: UUID
    name: str
    description: str
    parameters: Dict[str, Any]  # This is the JSON schema format
    code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UpdateFunctionRequest(BaseModel):
    description: Optional[str] = None
    parameters: Optional[List[FunctionParameter]] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None