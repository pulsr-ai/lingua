from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.base import get_db
from app.db.models import Memory as MemoryModel, Subtenant as SubtenantModel
from app.schemas.memory import Memory, MemoryCreate, MemoryUpdate

router = APIRouter()


@router.post("/subtenants/{subtenant_id}/memories", response_model=Memory)
def create_memory(
    subtenant_id: UUID,
    memory: MemoryCreate,
    db: Session = Depends(get_db)
):
    # Verify subtenant exists
    subtenant = db.query(SubtenantModel).filter(SubtenantModel.id == subtenant_id).first()
    if not subtenant:
        raise HTTPException(status_code=404, detail="Subtenant not found")
    
    # Check if memory with this key already exists
    existing = db.query(MemoryModel).filter(
        MemoryModel.subtenant_id == subtenant_id,
        MemoryModel.key == memory.key
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Memory with this key already exists")
    
    db_memory = MemoryModel(
        subtenant_id=subtenant_id,
        key=memory.key,
        value=memory.value
    )
    db.add(db_memory)
    db.commit()
    db.refresh(db_memory)
    return db_memory


@router.get("/subtenants/{subtenant_id}/memories", response_model=List[Memory])
def list_memories(
    subtenant_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Verify subtenant exists
    subtenant = db.query(SubtenantModel).filter(SubtenantModel.id == subtenant_id).first()
    if not subtenant:
        raise HTTPException(status_code=404, detail="Subtenant not found")
    
    memories = db.query(MemoryModel).filter(
        MemoryModel.subtenant_id == subtenant_id
    ).offset(skip).limit(limit).all()
    return memories


@router.get("/subtenants/{subtenant_id}/memories/{key}", response_model=Memory)
def get_memory(
    subtenant_id: UUID,
    key: str,
    db: Session = Depends(get_db)
):
    memory = db.query(MemoryModel).filter(
        MemoryModel.subtenant_id == subtenant_id,
        MemoryModel.key == key
    ).first()
    
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return memory


@router.put("/subtenants/{subtenant_id}/memories/{key}", response_model=Memory)
def update_memory(
    subtenant_id: UUID,
    key: str,
    memory: MemoryUpdate,
    db: Session = Depends(get_db)
):
    db_memory = db.query(MemoryModel).filter(
        MemoryModel.subtenant_id == subtenant_id,
        MemoryModel.key == key
    ).first()
    
    if not db_memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    db_memory.value = memory.value
    db.commit()
    db.refresh(db_memory)
    return db_memory


@router.delete("/subtenants/{subtenant_id}/memories/{key}")
def delete_memory(
    subtenant_id: UUID,
    key: str,
    db: Session = Depends(get_db)
):
    memory = db.query(MemoryModel).filter(
        MemoryModel.subtenant_id == subtenant_id,
        MemoryModel.key == key
    ).first()
    
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    db.delete(memory)
    db.commit()
    return {"message": "Memory deleted successfully"}