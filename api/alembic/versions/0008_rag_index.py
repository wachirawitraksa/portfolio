"""rag: glossary and search index

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

EMBED_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table('glossary_entry',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('terms', postgresql.ARRAY(sa.Text()), nullable=False),
    sa.Column('note', sa.String(length=200), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('rag_chunk',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_type', sa.String(length=16), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('section', sa.String(length=24), nullable=False),
    sa.Column('title_th', sa.String(length=300), nullable=False),
    sa.Column('title_en', sa.String(length=300), nullable=False),
    sa.Column('body_th', sa.Text(), nullable=False),
    sa.Column('body_en', sa.Text(), nullable=False),
    sa.Column('search_text', sa.Text(), nullable=False),
    sa.Column('sound', sa.Text(), nullable=False),
    sa.Column('embedding', Vector(EMBED_DIM), nullable=False),
    sa.Column('built_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rag_chunk_search_trgm', 'rag_chunk', ['search_text'], postgresql_using='gin', postgresql_ops={'search_text': 'gin_trgm_ops'})
    op.create_index('ix_rag_chunk_sound_trgm', 'rag_chunk', ['sound'], postgresql_using='gin', postgresql_ops={'sound': 'gin_trgm_ops'})


def downgrade() -> None:
    op.drop_index('ix_rag_chunk_sound_trgm', table_name='rag_chunk')
    op.drop_index('ix_rag_chunk_search_trgm', table_name='rag_chunk')
    op.drop_table('rag_chunk')
    op.drop_table('glossary_entry')
