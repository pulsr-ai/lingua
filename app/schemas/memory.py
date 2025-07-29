from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class MemoryBase(BaseModel):
    key: str
    value: str


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    value: str


class Memory(MemoryBase):
    id: UUID
    subtenant_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True