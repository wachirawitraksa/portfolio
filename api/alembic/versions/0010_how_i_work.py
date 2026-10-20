"""site settings: which project tells the "how I work" story

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa


revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site_settings', sa.Column('how_i_work_project_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'site_settings_how_i_work_project_id_fkey', 'site_settings', 'project', ['how_i_work_project_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('site_settings_how_i_work_project_id_fkey', 'site_settings', type_='foreignkey')
    op.drop_column('site_settings', 'how_i_work_project_id')
