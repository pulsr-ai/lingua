import logging
from typing import List, Dict, Any, Optional, Generator, AsyncGenerator
from sqlalchemy.orm import Session
from uuid import UUID
import time
import json

from app.db.models import Message as MessageModel, Chat as ChatModel, Memory as MemoryModel, RequestLog
from app.schemas.message import MessageCreate, MessageSendRequest, MessageSendResponse, Message, MessageRole
from app.providers.factory import LLMProviderFactory
from app.schemas.llm import LLMRequest
from app.core.functions import function_registry
from app.core.mcp_client import mcp_client
from app.core.config import settings
from fastapi import BackgroundTasks
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class MessageService:
    """Service for handling message operations"""
    
    @staticmethod
    def _prepare_chat_context(
        chat_id: UUID,
        request: MessageSendRequest,
        db: Session,
        chat: ChatModel
    ) -> tuple[MessageModel, List[Dict[str, Any]], List[str], List[str], List[Dict[str, Any]]]:
        """Prepare chat context including user message, message history, tools, and memories.
        Returns: (user_message, llm_messages, enabled_functions, enabled_mcp_tools, available_tools)
        """
        # Prepare tools first to get the configuration
        available_tools, enabled_functions, enabled_mcp_tools = MessageService._prepare_tools(request, chat)
        
        # Save user message with tool configuration
        user_message = MessageModel(
            chat_id=chat_id,
            role=MessageRole.USER.value,
            content=request.content,
            enabled_functions=enabled_functions,
            enabled_mcp_tools=enabled_mcp_tools
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # Get all messages in the chat
        messages = db.query(MessageModel).filter(
            MessageModel.chat_id == chat_id
        ).order_by(MessageModel.created_at).all()
        
        # Convert to format for LLM
        llm_messages = []
        for msg in messages:
            llm_msg = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.name:
                llm_msg["name"] = msg.name
            if msg.tool_call_id:
                llm_msg["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                llm_msg["tool_calls"] = msg.tool_calls
            llm_messages.append(llm_msg)
        
        # Add memories if requested
        if request.include_memories:
            memories = db.query(MemoryModel).filter(
                MemoryModel.subtenant_id == chat.subtenant_id
            ).all()
            
            if memories:
                memory_content = "User context:\n"
                for memory in memories:
                    memory_content += f"- {memory.key}: {memory.value}\n"
                
                # Insert memories as a system message at the beginning
                llm_messages.insert(0, {
                    "role": MessageRole.SYSTEM.value,
                    "content": memory_content
                })
        
        return user_message, llm_messages, enabled_functions, enabled_mcp_tools, available_tools
    
    @staticmethod
    def _prepare_tools(request: MessageSendRequest, chat: ChatModel) -> tuple[List[Dict[str, Any]], List[str], List[str]]:
        """Prepare available tools based on chat defaults and request overrides.
        Returns: (tools, enabled_functions, enabled_mcp_tools)
        """
        tools = []
        
        # Get all registered functions
        all_function_tools = function_registry.get_definitions()
        
        # Determine which functions to enable
        # Priority: request overrides > chat defaults > all functions
        enabled_functions = None
        if request.enabled_functions is not None:
            # Request explicitly specifies which functions to enable
            enabled_functions = request.enabled_functions
        elif chat.enabled_functions is not None:
            # Use chat's default enabled functions
            enabled_functions = chat.enabled_functions
        
        # Filter registered functions
        if enabled_functions is not None:
            # Only include explicitly enabled functions
            function_tools = [
                tool for tool in all_function_tools 
                if tool["function"]["name"] in enabled_functions
            ]
        elif request.disabled_functions is not None:
            # Include all except explicitly disabled functions
            function_tools = [
                tool for tool in all_function_tools 
                if tool["function"]["name"] not in request.disabled_functions
            ]
        else:
            # Include all functions by default
            function_tools = all_function_tools
            enabled_functions = [tool["function"]["name"] for tool in all_function_tools]
        
        tools.extend(function_tools)
        
        # Get all MCP tools
        all_mcp_tools = mcp_client.get_tools_definitions()
        
        # Determine which MCP tools to enable
        # Priority: request overrides > chat defaults > all MCP tools
        enabled_mcp_tools = None
        if request.enabled_mcp_tools is not None:
            # Request explicitly specifies which MCP tools to enable
            enabled_mcp_tools = request.enabled_mcp_tools
        elif chat.enabled_mcp_tools is not None:
            # Use chat's default enabled MCP tools
            enabled_mcp_tools = chat.enabled_mcp_tools
        
        # Filter MCP tools
        if enabled_mcp_tools is not None:
            # Only include explicitly enabled MCP tools
            mcp_tools = [
                tool for tool in all_mcp_tools 
                if tool["function"]["name"] in enabled_mcp_tools
            ]
        elif request.disabled_mcp_tools is not None:
            # Include all except explicitly disabled MCP tools
            mcp_tools = [
                tool for tool in all_mcp_tools 
                if tool["function"]["name"] not in request.disabled_mcp_tools
            ]
        else:
            # Include all MCP tools by default
            mcp_tools = all_mcp_tools
            enabled_mcp_tools = [tool["function"]["name"] for tool in all_mcp_tools]
        
        tools.extend(mcp_tools)
        
        
        # Ensure we have lists even if no tools were selected
        if enabled_functions is None:
            enabled_functions = [tool["function"]["name"] for tool in function_tools]
        if enabled_mcp_tools is None:
            enabled_mcp_tools = [tool["function"]["name"] for tool in mcp_tools]
        
        return (tools if tools else None, enabled_functions, enabled_mcp_tools)
    
    @staticmethod
    async def _execute_function(name: str, arguments: Dict[str, Any]) -> str:
        """Execute a function and return the result as a string"""
        try:
            # Try to execute as a registered function (this will load from DB if needed)
            try:
                result = await function_registry.execute(name, arguments)
                return json.dumps(result) if not isinstance(result, str) else result
            except ValueError:
                # Function not found in registry, try MCP tools
                pass
            
            # Check if it's an MCP tool
            handler = mcp_client.get_tool_handler(name)
            if handler:
                result = await handler.execute(**arguments)
                return json.dumps(result) if not isinstance(result, str) else result
            
            # If not found anywhere, return error
            return json.dumps({"error": f"Function '{name}' not found"})
            
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    @staticmethod
    async def send_message(
        chat_id: UUID,
        request: MessageSendRequest,
        db: Session,
        background_tasks: BackgroundTasks
    ) -> MessageSendResponse:
        logger.info(f"Sending message to chat {chat_id}")
        # Get chat and verify it exists
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Prepare chat context
        user_message, llm_messages, enabled_functions, enabled_mcp_tools, available_tools = \
            MessageService._prepare_chat_context(chat_id, request, db, chat)
        
        logger.info("Preparing LLM request")
        
        # Create LLM request
        llm_request = LLMRequest(
            messages=llm_messages,
            tools=available_tools if available_tools else None,
            tool_choice=request.tool_choice,
            stream=False,
            model=request.model or settings.default_model  # Use request model or default
        )
        
        # Get provider and make request
        provider = LLMProviderFactory.create_provider(provider_name=request.provider_name)
        
        # Log request start
        start_time = time.time()
        request_log = RequestLog(
            subtenant_id=chat.subtenant_id,
            chat_id=chat_id,
            message_id=user_message.id,
            provider=provider.name,
            model=llm_request.model or provider.default_model,
            request_data={
                "messages": llm_messages[-10:],  # Log last 10 messages
                "tools": len(available_tools) if available_tools else 0,
                "has_tools": bool(available_tools)
            }
        )
        
        try:
            # Get LLM response
            llm_response = provider.complete(llm_request)
            
            # Check if the response contains tool calls
            if llm_response.tool_calls:
                # Save assistant message with tool calls
                assistant_message = MessageModel(
                    chat_id=chat_id,
                    role=MessageRole.ASSISTANT.value,
                    content=llm_response.content or "",
                    tool_calls=[tc.model_dump() for tc in llm_response.tool_calls] if llm_response.tool_calls else None,
                    enabled_functions=enabled_functions,
                    enabled_mcp_tools=enabled_mcp_tools
                )
                db.add(assistant_message)
                db.commit()
                
                # Execute tools/functions
                tool_results = []
                
                # Handle tool calls
                for tool_call in llm_response.tool_calls:
                    tool_id = tool_call.id
                    function_data = tool_call.function
                    function_name = function_data['name']
                    function_args = json.loads(function_data.get('arguments', '{}'))
                    
                    # Execute function and get result
                    function_result = await MessageService._execute_function(function_name, function_args)
                    
                    # Save tool result as a message
                    tool_message = MessageModel(
                        chat_id=chat_id,
                        role=MessageRole.TOOL.value,
                        tool_call_id=tool_id,
                        name=function_name,
                        content=function_result
                    )
                    db.add(tool_message)
                    tool_results.append(function_result)
                
                db.commit()
                
                # Get updated messages including function result
                messages = db.query(MessageModel).filter(
                    MessageModel.chat_id == chat_id
                ).order_by(MessageModel.created_at).all()
                
                # Convert to format for LLM
                updated_llm_messages = []
                for msg in messages:
                    llm_msg = {
                        "role": msg.role
                    }
                    if msg.content:
                        llm_msg["content"] = msg.content
                    if msg.name:
                        llm_msg["name"] = msg.name
                    if msg.tool_call_id:
                        llm_msg["tool_call_id"] = msg.tool_call_id
                    if msg.tool_calls:
                        llm_msg["tool_calls"] = msg.tool_calls
                    updated_llm_messages.append(llm_msg)
                
                # Make another LLM call with the tool results
                followup_request = LLMRequest(
                    messages=updated_llm_messages,
                    tools=available_tools if available_tools else None,
                    tool_choice=request.tool_choice,
                    stream=False,
                    model=llm_request.model  # Pass original model to followup request
                )
                
                # Get final response
                logger.info("Getting final LLM response after function call")
                final_response = provider.complete(followup_request)
                logger.info("Received final LLM response")
                
                # Save final assistant message
                final_message = MessageModel(
                    chat_id=chat_id,
                    role=final_response.role,
                    content=final_response.content,
                    enabled_functions=enabled_functions,
                    enabled_mcp_tools=enabled_mcp_tools
                )
                db.add(final_message)
                
                # Update request log
                request_log.response_data = {
                    "content": final_response.content[:1000],
                    "tool_calls": [tc.model_dump() for tc in llm_response.tool_calls] if llm_response.tool_calls else None,
                    "tool_results": tool_results
                }
                request_log.tokens_prompt = final_response.usage.get("prompt_tokens") if final_response.usage else None
                request_log.tokens_completion = final_response.usage.get("completion_tokens") if final_response.usage else None
                request_log.tokens_total = final_response.usage.get("total_tokens") if final_response.usage else None
                request_log.latency_ms = int((time.time() - start_time) * 1000)
                request_log.status_code = 200
                
                db.add(request_log)
                db.commit()
                db.refresh(final_message)
                
                return MessageSendResponse(
                    message=Message.model_validate(final_message),
                    usage=final_response.usage
                )
            
            else:
                # No function call, save regular message
                assistant_message = MessageModel(
                    chat_id=chat_id,
                    role=llm_response.role,
                    content=llm_response.content,
                    enabled_functions=enabled_functions,
                    enabled_mcp_tools=enabled_mcp_tools
                )
                db.add(assistant_message)
                
                # Update request log
                request_log.response_data = {
                    "content": llm_response.content[:1000]
                }
                request_log.tokens_prompt = llm_response.usage.get("prompt_tokens") if llm_response.usage else None
                request_log.tokens_completion = llm_response.usage.get("completion_tokens") if llm_response.usage else None
                request_log.tokens_total = llm_response.usage.get("total_tokens") if llm_response.usage else None
                request_log.latency_ms = int((time.time() - start_time) * 1000)
                request_log.status_code = 200
                
                db.add(request_log)
                db.commit()
                db.refresh(assistant_message)
                
                return MessageSendResponse(
                    message=Message.model_validate(assistant_message),
                    usage=llm_response.usage
                )
            
        except Exception as e:
            # Log error
            request_log.error = str(e)
            request_log.status_code = 500
            request_log.latency_ms = int((time.time() - start_time) * 1000)
            db.add(request_log)
            db.commit()
            raise
    
    @staticmethod
    async def stream_message(
        chat_id: UUID,
        request: MessageSendRequest,
        db: Session,
        provider_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Send a message and stream the response"""
        
        # Get chat and verify it exists
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Prepare chat context
        user_message, llm_messages, enabled_functions, enabled_mcp_tools, available_tools = \
            MessageService._prepare_chat_context(chat_id, request, db, chat)
        
        # Create LLM request
        llm_request = LLMRequest(
            messages=llm_messages,
            tools=available_tools if available_tools else None,
            tool_choice=request.tool_choice,
            stream=True,
            model=request.model or settings.default_model
        )
        
        # Get provider and make request
        provider = LLMProviderFactory.create_provider(provider_name=request.provider_name or provider_name)
        
        # Log request start
        start_time = time.time()
        request_log = RequestLog(
            subtenant_id=chat.subtenant_id,
            chat_id=chat_id,
            message_id=user_message.id,
            provider=provider.name,
            model=llm_request.model or provider.default_model,
            request_data={
                "messages": llm_messages[-10:],  # Log last 10 messages
                "streaming": True
            }
        )
        
        try:
            # For streaming with tool calls, we need to collect the full response first
            # For now, treat all streaming as sync to avoid complex async tool call handling
            # The async provider streaming with tool calls has issues, so fall back to sync approach
            full_content = ""
            
            # Use sync streaming regardless of provider type
            if hasattr(provider, 'astream'):
                # Async provider - collect content without trying to handle tool calls in streaming
                async for chunk in provider.astream(llm_request):
                    if isinstance(chunk, str):
                        full_content += chunk
                        yield chunk
                    else:
                        chunk_str = str(chunk)
                        full_content += chunk_str
                        yield chunk_str
            else:
                # Sync provider
                for chunk in provider.stream(llm_request):
                    full_content += chunk
                    yield chunk
                
            # After streaming is complete, save the response 
            # For now, streaming doesn't handle tool calls - it just returns the streamed content
            assistant_message = MessageModel(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT.value,
                content=full_content,
                enabled_functions=enabled_functions,
                enabled_mcp_tools=enabled_mcp_tools
            )
            db.add(assistant_message)
            
            # Update request log
            request_log.response_data = {
                "content": full_content[:1000],
                "streaming": True
            }
            
            request_log.latency_ms = int((time.time() - start_time) * 1000)
            request_log.status_code = 200
            db.add(request_log)
            db.commit()
            
        except Exception as e:
            # Log error
            request_log.error = str(e)
            request_log.status_code = 500
            request_log.latency_ms = int((time.time() - start_time) * 1000)
            db.add(request_log)
            db.commit()
            raise