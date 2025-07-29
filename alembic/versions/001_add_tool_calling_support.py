"""Add tool calling support

Revision ID: 001_add_tool_calling_support
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '001_add_tool_calling_support'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create subtenants table
    op.create_table('subtenants',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create chats table
    op.create_table('chats',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('subtenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['subtenant_id'], ['subtenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create messages table with tool calling support
    op.create_table('messages',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('tool_calls', sa.JSON(), nullable=True),
        sa.Column('tool_call_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('function_call', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create memories table
    op.create_table('memories',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('subtenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['subtenant_id'], ['subtenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subtenant_id', 'key')
    )
    
    # Create request_logs table
    op.create_table('request_logs',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('subtenant_id', UUID(as_uuid=True), nullable=True),
        sa.Column('chat_id', UUID(as_uuid=True), nullable=True),
        sa.Column('message_id', UUID(as_uuid=True), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('request_data', sa.JSON(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('tokens_prompt', sa.Integer(), nullable=True),
        sa.Column('tokens_completion', sa.Integer(), nullable=True),
        sa.Column('tokens_total', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['subtenant_id'], ['subtenants.id'], ),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('request_logs')
    op.drop_table('memories')
    op.drop_table('messages')
    op.drop_table('chats')
    op.drop_table('subtenants')