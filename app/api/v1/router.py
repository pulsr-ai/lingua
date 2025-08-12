from fastapi import APIRouter

from app.api.v1.endpoints import (
    subtenants,
    chats,
    messages,
    messages_send,
    memories,
    llm,
    functions,
    mcp,
    tools,
    assistants
)

api_router = APIRouter()

api_router.include_router(subtenants.router, prefix="/subtenants", tags=["subtenants"])
api_router.include_router(chats.router, tags=["chats"])
api_router.include_router(messages.router, tags=["messages"])
api_router.include_router(messages_send.router, tags=["messages"])
api_router.include_router(memories.router, tags=["memories"])
api_router.include_router(llm.router, tags=["llm"])
api_router.include_router(functions.router, tags=["functions"])
api_router.include_router(mcp.router, tags=["mcp"])
api_router.include_router(tools.router, tags=["tools"])
api_router.include_router(assistants.router, tags=["assistants"])