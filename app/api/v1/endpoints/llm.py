from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
import json

from app.schemas.llm import LLMRequest, LLMResponse
from app.providers.factory import LLMProviderFactory
from app.db.models import RequestLog, Subtenant
from app.db.base import get_db
import time

router = APIRouter()


@router.post("/subtenants/{subtenant_id}/llm/complete", response_model=LLMResponse)
async def complete(subtenant_id: UUID, request: LLMRequest, db: Session = Depends(get_db)):
    """Direct LLM completion without chat context"""
    # Verify subtenant exists
    subtenant = db.query(Subtenant).filter(Subtenant.id == subtenant_id).first()
    if not subtenant:
        raise HTTPException(status_code=404, detail="Subtenant not found")
    
    start_time = time.time()
    llm_provider = LLMProviderFactory.create_provider(provider_name=request.provider_name)
    
    # Create request log
    request_log = RequestLog(
        subtenant_id=subtenant_id,  # Track subtenant for direct LLM calls
        chat_id=None,       # No chat for direct LLM calls
        message_id=None,    # No message for direct LLM calls
        provider=llm_provider.name,
        model=request.model or llm_provider.default_model,
        request_data={
            "messages": request.messages,
            "tools": len(request.tools) if request.tools else 0,
            "direct_llm_call": True
        }
    )
    
    try:
        response = await llm_provider.acomplete(request)
        
        # Update request log with response data
        request_log.response_data = {
            "content": response.content[:1000] if response.content else None,
            "tool_calls": len(response.tool_calls) if response.tool_calls else 0
        }
        request_log.tokens_prompt = response.usage.get("prompt_tokens") if response.usage else None
        request_log.tokens_completion = response.usage.get("completion_tokens") if response.usage else None
        request_log.tokens_total = response.usage.get("total_tokens") if response.usage else None
        request_log.latency_ms = int((time.time() - start_time) * 1000)
        request_log.status_code = 200
        
        db.add(request_log)
        db.commit()
        
        return response
    except Exception as e:
        # Log error
        request_log.error = str(e)
        request_log.status_code = 500
        request_log.latency_ms = int((time.time() - start_time) * 1000)
        db.add(request_log)
        db.commit()
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subtenants/{subtenant_id}/llm/stream")
async def stream_complete(
    subtenant_id: UUID,
    request: LLMRequest,
    db: Session = Depends(get_db),
    provider: Optional[str] = None
):
    """Direct LLM streaming completion without chat context"""
    # Verify subtenant exists
    subtenant = db.query(Subtenant).filter(Subtenant.id == subtenant_id).first()
    if not subtenant:
        raise HTTPException(status_code=404, detail="Subtenant not found")
    
    start_time = time.time()
    llm_provider = LLMProviderFactory.create_provider(provider or request.provider_name)
    request.stream = True
    
    # Create request log
    request_log = RequestLog(
        subtenant_id=subtenant_id,  # Track subtenant for direct LLM calls
        chat_id=None,       # No chat for direct LLM calls
        message_id=None,    # No message for direct LLM calls
        provider=llm_provider.name,
        model=request.model or llm_provider.default_model,
        request_data={
            "messages": request.messages,
            "tools": len(request.tools) if request.tools else 0,
            "direct_llm_call": True,
            "streaming": True
        }
    )
    
    try:
        total_content = ""
        token_count = 0
        
        async def generate():
            nonlocal total_content, token_count
            async for chunk in llm_provider.astream(request):
                total_content += chunk
                token_count += 1  # Rough estimate
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
            
            # Log after streaming completes
            request_log.response_data = {
                "content": total_content[:1000],
                "estimated_tokens": token_count
            }
            request_log.latency_ms = int((time.time() - start_time) * 1000)
            request_log.status_code = 200
            db.add(request_log)
            db.commit()
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        # Log error
        request_log.error = str(e)
        request_log.status_code = 500
        request_log.latency_ms = int((time.time() - start_time) * 1000)
        db.add(request_log)
        db.commit()
        
        raise HTTPException(status_code=500, detail=str(e))