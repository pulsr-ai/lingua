from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class SubtenantBase(BaseModel):
    pass


class SubtenantCreate(SubtenantBase):
    pass


class SubtenantUpdate(SubtenantBase):
    pass


class Subtenant(SubtenantBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True