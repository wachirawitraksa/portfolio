"""work history timeline

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('work_entry',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('position_th', sa.String(length=200), nullable=False),
    sa.Column('position_en', sa.String(length=200), nullable=False),
    sa.Column('employer', sa.String(length=200), nullable=False),
    sa.Column('employment_type', sa.String(length=20), nullable=False),
    sa.Column('started_on', sa.Date(), nullable=False),
    sa.Column('ended_on', sa.Date(), nullable=True),
    sa.Column('ongoing', sa.Boolean(), nullable=False),
    sa.Column('bullets_th', sa.Text(), nullable=False),
    sa.Column('bullets_en', sa.Text(), nullable=False),
    sa.Column('hidden', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('work_tag',
    sa.Column('work_entry_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['work_entry_id'], ['work_entry.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('work_entry_id', 'tag_id')
    )


def downgrade() -> None:
    op.drop_table('work_tag')
    op.drop_table('work_entry')
