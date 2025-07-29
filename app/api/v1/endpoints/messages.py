from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.base import get_db
from app.db.models import Message as MessageModel, Chat as ChatModel
from app.schemas.message import Message, MessageCreate

router = APIRouter()


@router.get("/chats/{chat_id}/messages", response_model=List[Message])
def list_messages(
    chat_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Verify chat exists
    chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    messages = db.query(MessageModel).filter(
        MessageModel.chat_id == chat_id
    ).order_by(MessageModel.created_at).offset(skip).limit(limit).all()
    return messages