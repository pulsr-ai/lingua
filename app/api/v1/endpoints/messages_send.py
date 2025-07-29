from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
import json

from app.db.base import get_db
from app.schemas.message import MessageSendRequest, MessageSendResponse
from app.services.message_service import MessageService

router = APIRouter()


@router.post("/chats/{chat_id}/messages", response_model=MessageSendResponse)
async def send_message(
    chat_id: UUID,
    request: MessageSendRequest,
    provider: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Send a message synchronously"""
    try:
        return await MessageService.send_message(chat_id, request, db, provider)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/messages/stream")
def stream_message(
    chat_id: UUID,
    request: MessageSendRequest,
    provider: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Send a message and stream the response"""
    try:
        def generate():
            for chunk in MessageService.stream_message(chat_id, request, db, provider):
                # Format as Server-Sent Events
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))