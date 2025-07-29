from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer, func
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
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    subtenant = relationship("Subtenant", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system, function, tool
    content = Column(Text, nullable=True)  # Can be null for tool calls
    tool_calls = Column(JSON)  # For storing tool call data (new format)
    tool_call_id = Column(String(255))  # For tool response messages
    name = Column(String(255))  # For function/tool messages
    # Keep backwards compatibility
    function_call = Column(JSON)  # For storing function call data (deprecated)
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
        {"postgresql_indexes": [{"unique": True, "columns": ["subtenant_id", "key"]}]},
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