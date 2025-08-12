from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.base import get_db
from app.db.models import Chat as ChatModel, Subtenant as SubtenantModel, Message as MessageModel, Assistant as AssistantModel
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
    
    # If assistant_id is provided, verify it exists and is accessible
    assistant = None
    if chat.assistant_id:
        assistant = db.query(AssistantModel).filter(
            AssistantModel.id == chat.assistant_id,
            AssistantModel.is_active == True
        ).first()
        if not assistant:
            raise HTTPException(status_code=404, detail="Assistant not found")
        
        # Check if assistant is accessible (workspace-wide or belongs to this subtenant)
        if assistant.subtenant_id and assistant.subtenant_id != subtenant_id:
            raise HTTPException(status_code=403, detail="Assistant not accessible for this subtenant")
    
    # Create the chat with assistant settings
    db_chat = ChatModel(
        subtenant_id=subtenant_id,
        assistant_id=chat.assistant_id,
        title=chat.title,
        enabled_functions=chat.enabled_functions,
        enabled_mcp_tools=chat.enabled_mcp_tools
    )
    
    # If assistant is provided, apply its presets to the chat (if not overridden)
    if assistant:
        if not chat.enabled_functions and assistant.enabled_functions:
            db_chat.enabled_functions = assistant.enabled_functions
        if not chat.enabled_mcp_tools and assistant.enabled_mcp_tools:
            db_chat.enabled_mcp_tools = assistant.enabled_mcp_tools
    
    db.add(db_chat)
    db.flush()  # Flush to get the ID for the message

    # Add system message if provided by chat or assistant
    system_content = chat.system_message or (assistant.system_prompt if assistant else None)
    if system_content:
        system_message = MessageModel(
            chat_id=db_chat.id,
            role="system",
            content=system_content
        )
        db.add(system_message)

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