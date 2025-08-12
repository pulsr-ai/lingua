from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID

from app.db.base import get_db
from app.db.models import Assistant as AssistantModel, Subtenant as SubtenantModel
from app.schemas.assistant import Assistant, AssistantCreate, AssistantUpdate, AssistantList

router = APIRouter()


@router.post("/assistants", response_model=Assistant)
def create_assistant(
    assistant: AssistantCreate,
    db: Session = Depends(get_db)
):
    # If subtenant_id is provided, verify it exists
    if assistant.subtenant_id:
        subtenant = db.query(SubtenantModel).filter(SubtenantModel.id == assistant.subtenant_id).first()
        if not subtenant:
            raise HTTPException(status_code=404, detail="Subtenant not found")
    
    db_assistant = AssistantModel(
        subtenant_id=assistant.subtenant_id,
        name=assistant.name,
        description=assistant.description,
        system_prompt=assistant.system_prompt,
        enabled_functions=assistant.enabled_functions,
        enabled_mcp_tools=assistant.enabled_mcp_tools,
        function_parameters=assistant.function_parameters,
        mcp_tool_parameters=assistant.mcp_tool_parameters,
        is_active=True
    )
    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)
    return db_assistant


@router.get("/assistants", response_model=AssistantList)
def list_assistants(
    subtenant_id: Optional[UUID] = Query(None, description="Filter by subtenant (includes workspace-wide if specified)"),
    workspace_only: bool = Query(False, description="Only show workspace-wide assistants"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(AssistantModel).filter(AssistantModel.is_active == True)
    
    if workspace_only:
        # Only workspace-wide assistants
        query = query.filter(AssistantModel.subtenant_id == None)
    elif subtenant_id:
        # Both workspace-wide and specific subtenant's assistants
        query = query.filter(
            or_(
                AssistantModel.subtenant_id == None,
                AssistantModel.subtenant_id == subtenant_id
            )
        )
    # If neither flag is set, return all assistants
    
    total = query.count()
    assistants = query.offset(skip).limit(limit).all()
    
    return AssistantList(assistants=assistants, total=total)


@router.get("/assistants/{assistant_id}", response_model=Assistant)
def get_assistant(
    assistant_id: UUID,
    db: Session = Depends(get_db)
):
    assistant = db.query(AssistantModel).filter(
        AssistantModel.id == assistant_id,
        AssistantModel.is_active == True
    ).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return assistant


@router.put("/assistants/{assistant_id}", response_model=Assistant)
def update_assistant(
    assistant_id: UUID,
    assistant: AssistantUpdate,
    db: Session = Depends(get_db)
):
    db_assistant = db.query(AssistantModel).filter(
        AssistantModel.id == assistant_id
    ).first()
    if not db_assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Update fields if provided
    if assistant.name is not None:
        db_assistant.name = assistant.name
    if assistant.description is not None:
        db_assistant.description = assistant.description
    if assistant.system_prompt is not None:
        db_assistant.system_prompt = assistant.system_prompt
    if assistant.enabled_functions is not None:
        db_assistant.enabled_functions = assistant.enabled_functions
    if assistant.enabled_mcp_tools is not None:
        db_assistant.enabled_mcp_tools = assistant.enabled_mcp_tools
    if assistant.function_parameters is not None:
        db_assistant.function_parameters = assistant.function_parameters
    if assistant.mcp_tool_parameters is not None:
        db_assistant.mcp_tool_parameters = assistant.mcp_tool_parameters
    if assistant.is_active is not None:
        db_assistant.is_active = assistant.is_active
    
    db.commit()
    db.refresh(db_assistant)
    return db_assistant


@router.delete("/assistants/{assistant_id}")
def delete_assistant(
    assistant_id: UUID,
    db: Session = Depends(get_db)
):
    assistant = db.query(AssistantModel).filter(
        AssistantModel.id == assistant_id
    ).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    
    # Soft delete by setting is_active to False
    assistant.is_active = False
    db.commit()
    
    return {"message": "Assistant deleted successfully"}