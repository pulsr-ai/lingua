from typing import List, Dict, Any, Optional, Generator
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


class MessageService:
    """Service for handling message operations"""
    
    @staticmethod
    def _prepare_tools(custom_tools: Optional[List[Dict[str, Any]]], 
                      custom_functions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Prepare available tools combining registry, MCP, and custom tools"""
        tools = []
        
        # Add registered functions as tools
        tools.extend(function_registry.get_definitions())
        
        # Add MCP tools
        tools.extend(mcp_client.get_tools_definitions())
        
        # Add custom tools from request
        if custom_tools:
            tools.extend(custom_tools)
        
        # Convert legacy functions format to tools format for backwards compatibility
        if custom_functions:
            for func in custom_functions:
                tool = {
                    "type": "function",
                    "function": func
                }
                tools.append(tool)
        
        return tools if tools else None
    
    @staticmethod
    async def _execute_function(name: str, arguments: Dict[str, Any]) -> str:
        """Execute a function and return the result as a string"""
        try:
            # Check if it's a registered function
            if function_registry.get_function(name):
                result = await function_registry.execute(name, arguments)
                return json.dumps(result) if not isinstance(result, str) else result
            
            # Check if it's an MCP tool
            handler = mcp_client.get_tool_handler(name)
            if handler:
                result = await handler.execute(**arguments)
                return json.dumps(result) if not isinstance(result, str) else result
            
            # If not found, return error
            return json.dumps({"error": f"Function '{name}' not found"})
            
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    @staticmethod
    async def send_message(
        chat_id: UUID,
        request: MessageSendRequest,
        db: Session,
        provider_name: Optional[str] = None
    ) -> MessageSendResponse:
        """Send a message and get response synchronously"""
        
        # Get chat and verify it exists
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")
        
        # Save user message
        user_message = MessageModel(
            chat_id=chat_id,
            role=MessageRole.USER.value,
            content=request.content
        )
        db.add(user_message)
        db.commit()
        
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
            if msg.function_call:
                llm_msg["function_call"] = msg.function_call
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
        
        # Prepare tools for LLM
        available_tools = self._prepare_tools(request.tools, request.functions)
        
        # Create LLM request
        llm_request = LLMRequest(
            messages=llm_messages,
            tools=available_tools if available_tools else None,
            tool_choice=request.tool_choice,
            stream=False
        )
        
        # Get provider and make request
        provider = LLMProviderFactory.create_provider(provider_name)
        
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
                "functions": request.functions
            }
        )
        
        try:
            # Get LLM response
            llm_response = provider.complete(llm_request)
            
            # Check if the response contains tool calls (new format) or function call (legacy)
            if llm_response.tool_calls or llm_response.function_call:
                # Save assistant message with tool calls
                assistant_message = MessageModel(
                    chat_id=chat_id,
                    role=MessageRole.ASSISTANT.value,
                    content=llm_response.content or "",
                    tool_calls=llm_response.tool_calls,
                    function_call=llm_response.function_call  # Keep for backwards compatibility
                )
                db.add(assistant_message)
                db.commit()
                
                # Execute tools/functions
                tool_results = []
                
                # Handle new tool calls format
                if llm_response.tool_calls:
                    for tool_call in llm_response.tool_calls:
                        tool_id = tool_call["id"]
                        function_name = tool_call["function"]["name"]
                        function_args = json.loads(tool_call["function"]["arguments"])
                        
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
                
                # Handle legacy function call format
                elif llm_response.function_call:
                    function_name = llm_response.function_call["name"]
                    function_args = json.loads(llm_response.function_call.get("arguments", "{}"))
                    
                    # Execute function and get result
                    function_result = await MessageService._execute_function(function_name, function_args)
                    
                    # Save function result as a message
                    function_message = MessageModel(
                        chat_id=chat_id,
                        role=MessageRole.FUNCTION.value,
                        name=function_name,
                        content=function_result
                    )
                    db.add(function_message)
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
                    if msg.function_call:
                        llm_msg["function_call"] = msg.function_call
                    updated_llm_messages.append(llm_msg)
                
                # Make another LLM call with the tool results
                followup_request = LLMRequest(
                    messages=updated_llm_messages,
                    tools=available_tools if available_tools else None,
                    tool_choice=request.tool_choice,
                    stream=False
                )
                
                # Get final response
                final_response = provider.complete(followup_request)
                
                # Save final assistant message
                final_message = MessageModel(
                    chat_id=chat_id,
                    role=final_response.role,
                    content=final_response.content,
                    function_call=final_response.function_call
                )
                db.add(final_message)
                
                # Update request log
                request_log.response_data = {
                    "content": final_response.content[:1000],
                    "function_call": llm_response.function_call,
                    "function_result": function_result[:500]
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
                    function_call=llm_response.function_call
                )
                db.add(assistant_message)
                
                # Update request log
                request_log.response_data = {
                    "content": llm_response.content[:1000],
                    "function_call": llm_response.function_call
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
    def stream_message(
        chat_id: UUID,
        request: MessageSendRequest,
        db: Session,
        provider_name: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Send a message and stream the response"""
        
        # Get chat and verify it exists
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            raise ValueError(f"Chat {chat_id} not found")
        
        # Save user message
        user_message = MessageModel(
            chat_id=chat_id,
            role=MessageRole.USER.value,
            content=request.content
        )
        db.add(user_message)
        db.commit()
        
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
            if msg.function_call:
                llm_msg["function_call"] = msg.function_call
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
                
                llm_messages.insert(0, {
                    "role": MessageRole.SYSTEM.value,
                    "content": memory_content
                })
        
        # Prepare tools for LLM
        available_tools = MessageService._prepare_tools(request.tools, request.functions)
        
        # Create LLM request
        llm_request = LLMRequest(
            messages=llm_messages,
            tools=available_tools if available_tools else None,
            tool_choice=request.tool_choice,
            stream=True
        )
        
        # Get provider
        provider = LLMProviderFactory.create_provider(provider_name)
        
        # Collect streamed content
        full_content = ""
        
        # Stream response
        for chunk in provider.stream(llm_request):
            full_content += chunk
            yield chunk
        
        # Save complete assistant message after streaming is done
        assistant_message = MessageModel(
            chat_id=chat_id,
            role="assistant",
            content=full_content
        )
        db.add(assistant_message)
        db.commit()