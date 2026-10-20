"""articles

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('article',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title_th', sa.String(length=200), nullable=False),
    sa.Column('title_en', sa.String(length=200), nullable=False),
    sa.Column('summary_th', sa.Text(), nullable=False),
    sa.Column('summary_en', sa.Text(), nullable=False),
    sa.Column('body_th', sa.Text(), nullable=False),
    sa.Column('body_en', sa.Text(), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('external_url', sa.String(length=500), nullable=False),
    sa.Column('platform', sa.String(length=80), nullable=False),
    sa.Column('published_on', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('article_tag',
    sa.Column('article_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['article.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('article_id', 'tag_id')
    )


def downgrade() -> None:
    op.drop_table('article_tag')
    op.drop_table('article')
