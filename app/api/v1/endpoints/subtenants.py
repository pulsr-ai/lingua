from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.base import get_db
from app.db.models import Subtenant as SubtenantModel
from app.schemas.subtenant import Subtenant, SubtenantCreate, SubtenantUpdate

router = APIRouter()


@router.post("/", response_model=Subtenant)
def create_subtenant(
    subtenant: SubtenantCreate,
    db: Session = Depends(get_db)
):
    db_subtenant = SubtenantModel()
    db.add(db_subtenant)
    db.commit()
    db.refresh(db_subtenant)
    return db_subtenant


@router.get("/", response_model=List[Subtenant])
def list_subtenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    subtenants = db.query(SubtenantModel).offset(skip).limit(limit).all()
    return subtenants


@router.get("/{subtenant_id}", response_model=Subtenant)
def get_subtenant(
    subtenant_id: UUID,
    db: Session = Depends(get_db)
):
    subtenant = db.query(SubtenantModel).filter(SubtenantModel.id == subtenant_id).first()
    if not subtenant:
        raise HTTPException(status_code=404, detail="Subtenant not found")
    return subtenant


@router.put("/{subtenant_id}", response_model=Subtenant)
def update_subtenant(
    subtenant_id: UUID,
    subtenant: SubtenantUpdate,
    db: Session = Depends(get_db)
):
    db_subtenant = db.query(SubtenantModel).filter(SubtenantModel.id == subtenant_id).first()
    if not db_subtenant:
        raise HTTPException(status_code=404, detail="Subtenant not found")
    
    db.commit()
    db.refresh(db_subtenant)
    return db_subtenant


@router.delete("/{subtenant_id}")
def delete_subtenant(
    subtenant_id: UUID,
    db: Session = Depends(get_db)
):
    subtenant = db.query(SubtenantModel).filter(SubtenantModel.id == subtenant_id).first()
    if not subtenant:
        raise HTTPException(status_code=404, detail="Subtenant not found")
    
    db.delete(subtenant)
    db.commit()
    return {"message": "Subtenant deleted successfully"}