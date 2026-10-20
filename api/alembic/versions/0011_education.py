"""education history

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa


revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('education_entry',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('institution_th', sa.String(length=200), nullable=False),
    sa.Column('institution_en', sa.String(length=200), nullable=False),
    sa.Column('level', sa.String(length=20), nullable=False),
    sa.Column('degree_th', sa.String(length=200), nullable=False),
    sa.Column('degree_en', sa.String(length=200), nullable=False),
    sa.Column('field_th', sa.String(length=200), nullable=False),
    sa.Column('field_en', sa.String(length=200), nullable=False),
    sa.Column('grade', sa.String(length=60), nullable=False),
    sa.Column('started_on', sa.Date(), nullable=False),
    sa.Column('ended_on', sa.Date(), nullable=True),
    sa.Column('ongoing', sa.Boolean(), nullable=False),
    sa.Column('details_th', sa.Text(), nullable=False),
    sa.Column('details_en', sa.Text(), nullable=False),
    sa.Column('hidden', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('education_entry')
