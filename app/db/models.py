from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer, Boolean, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base


class Subtenant(Base):
    __tablename__ = "subtenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    chats = relationship("Chat", back_populates="subtenant", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="subtenant", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subtenant_id = Column(UUID(as_uuid=True), ForeignKey("subtenants.id"), nullable=False)
    title = Column(String(255))
    # Default tool configuration for this chat (for Custom GPTs functionality)
    enabled_functions = Column(JSON)  # List of function names enabled by default
    enabled_mcp_tools = Column(JSON)  # List of MCP tool names enabled by default
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    subtenant = relationship("Subtenant", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=True)  # Can be null for tool calls
    tool_calls = Column(JSON)  # For storing tool call data
    tool_call_id = Column(String(255))  # For tool response messages
    name = Column(String(255))  # For function/tool messages
    # Store which tools were actually available when this message was processed
    enabled_functions = Column(JSON)  # List of function names that were enabled
    enabled_mcp_tools = Column(JSON)  # List of MCP tool names that were enabled
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    chat = relationship("Chat", back_populates="messages")


class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subtenant_id = Column(UUID(as_uuid=True), ForeignKey("subtenants.id"), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    subtenant = relationship("Subtenant", back_populates="memories")
    
    __table_args__ = (
        UniqueConstraint('subtenant_id', 'key', name='_subtenant_key_uc'),
    )


class RequestLog(Base):
    __tablename__ = "request_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subtenant_id = Column(UUID(as_uuid=True), ForeignKey("subtenants.id"))
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"))
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"))
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    request_data = Column(JSON)
    response_data = Column(JSON)
    tokens_prompt = Column(Integer)
    tokens_completion = Column(Integer)
    tokens_total = Column(Integer)
    latency_ms = Column(Integer)
    status_code = Column(Integer)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RegisteredFunction(Base):
    __tablename__ = "registered_functions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=False)  # Function parameter schema
    code = Column(Text, nullable=False)  # Python code for the function
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MCPServerModel(Base):
    __tablename__ = "mcp_servers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    url = Column(String(512), nullable=False)
    protocol = Column(String(50), default="websocket", nullable=False)  # websocket or http
    api_key = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_connected = Column(DateTime(timezone=True), nullable=True)
    connection_status = Column(String(50), default="disconnected", nullable=False)  # connected, disconnected, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)