"""project images

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('project_image',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=200), nullable=False),
    sa.Column('content_type', sa.String(length=50), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('caption_th', sa.String(length=300), nullable=False),
    sa.Column('caption_en', sa.String(length=300), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_cover', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_index('ix_project_image_project_id', 'project_image', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_project_image_project_id', table_name='project_image')
    op.drop_table('project_image')
