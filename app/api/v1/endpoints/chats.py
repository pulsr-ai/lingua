from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.base import get_db
from app.db.models import Chat as ChatModel, Subtenant as SubtenantModel
from app.schemas.chat import Chat, ChatCreate, ChatUpdate, ChatWithMessages

router = APIRouter()


@router.post("/subtenants/{subtenant_id}/chats", response_model=Chat)
def create_chat(
    subtenant_id: UUID,
    chat: ChatCreate,
    db: Session = Depends(get_db)
):
    # Verify subtenant exists
    subtenant = db.query(SubtenantModel).filter(SubtenantModel.id == subtenant_id).first()
    if not subtenant:
        raise HTTPException(status_code=404, detail="Subtenant not found")
    
    db_chat = ChatModel(
        subtenant_id=subtenant_id,
        title=chat.title
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat


@router.get("/subtenants/{subtenant_id}/chats", response_model=List[Chat])
def list_chats(
    subtenant_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Verify subtenant exists
    subtenant = db.query(SubtenantModel).filter(SubtenantModel.id == subtenant_id).first()
    if not subtenant:
        raise HTTPException(status_code=404, detail="Subtenant not found")
    
    chats = db.query(ChatModel).filter(
        ChatModel.subtenant_id == subtenant_id
    ).offset(skip).limit(limit).all()
    return chats


@router.get("/chats/{chat_id}", response_model=ChatWithMessages)
def get_chat(
    chat_id: UUID,
    db: Session = Depends(get_db)
):
    chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.put("/chats/{chat_id}", response_model=Chat)
def update_chat(
    chat_id: UUID,
    chat: ChatUpdate,
    db: Session = Depends(get_db)
):
    db_chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
    if not db_chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.title is not None:
        db_chat.title = chat.title
    
    db.commit()
    db.refresh(db_chat)
    return db_chat


@router.delete("/chats/{chat_id}")
def delete_chat(
    chat_id: UUID,
    db: Session = Depends(get_db)
):
    chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    db.delete(chat)
    db.commit()
    return {"message": "Chat deleted successfully"}