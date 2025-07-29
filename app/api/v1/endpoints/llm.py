from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json

from app.schemas.llm import LLMRequest, LLMResponse
from app.providers.factory import LLMProviderFactory

router = APIRouter()


@router.post("/llm/complete", response_model=LLMResponse)
def complete(
    request: LLMRequest,
    provider: Optional[str] = None
):
    """Direct LLM completion without chat context"""
    try:
        llm_provider = LLMProviderFactory.create_provider(provider)
        return llm_provider.complete(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm/stream")
def stream_complete(
    request: LLMRequest,
    provider: Optional[str] = None
):
    """Direct LLM streaming completion without chat context"""
    try:
        llm_provider = LLMProviderFactory.create_provider(provider)
        request.stream = True
        
        def generate():
            for chunk in llm_provider.stream(request):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))