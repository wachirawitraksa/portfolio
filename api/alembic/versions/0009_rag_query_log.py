"""question box log (also the answer cache)

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('rag_query',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ip_hash', sa.String(length=16), nullable=False),
    sa.Column('question', sa.String(length=300), nullable=False),
    sa.Column('normalized', sa.String(length=300), nullable=False),
    sa.Column('language', sa.String(length=8), nullable=False),
    sa.Column('band', sa.String(length=8), nullable=False),
    sa.Column('top_score', sa.Float(), nullable=False),
    sa.Column('mode', sa.String(length=16), nullable=False),
    sa.Column('tier', sa.String(length=8), nullable=False),
    sa.Column('cached', sa.Boolean(), nullable=False),
    sa.Column('cache_key', sa.String(length=32), nullable=False),
    sa.Column('answer', sa.Text(), nullable=False),
    sa.Column('sources', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rag_query_ip_created', 'rag_query', ['ip_hash', 'created_at'])
    op.create_index('ix_rag_query_cache', 'rag_query', ['cache_key', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_rag_query_cache', table_name='rag_query')
    op.drop_index('ix_rag_query_ip_created', table_name='rag_query')
    op.drop_table('rag_query')
