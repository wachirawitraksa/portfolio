"""projects tags

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

TEXT_FIELDS = ("title", "problem", "work", "role", "result", "learned", "next_steps")


def upgrade() -> None:
    op.create_table('tag',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('aliases', postgresql.ARRAY(sa.Text()), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    columns = [sa.Column('id', sa.Integer(), nullable=False)]
    for field in TEXT_FIELDS:
        kind = sa.String(length=200) if field == "title" else sa.Text()
        columns += [sa.Column(f'{field}_th', kind, nullable=False), sa.Column(f'{field}_en', kind, nullable=False)]
    columns += [
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('repo_url', sa.String(length=500), nullable=False),
        sa.Column('demo_url', sa.String(length=500), nullable=False),
        sa.Column('aliases', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('featured', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    ]
    op.create_table('project', *columns)
    op.create_table('project_category',
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['category.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('project_id', 'category_id')
    )
    op.create_table('project_tag',
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('project_id', 'tag_id')
    )


def downgrade() -> None:
    op.drop_table('project_tag')
    op.drop_table('project_category')
    op.drop_table('project')
    op.drop_table('tag')
