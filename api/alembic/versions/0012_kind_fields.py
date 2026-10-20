"""which groups of fields each kind's form shows

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None

ALL = "{tech,story,links,credential,year}"
# The kinds that migration 0003 created, by their English name. Anything else keeps every group.
DEFAULTS = {
    "Project": "{tech,story,links,year}",
    "Certificate": "{credential,year}",
    "Award": "{credential,year}",
    "Course": "{credential,tech,year}",
    "Activity": "{story,year}",
}


def upgrade() -> None:
    op.add_column(
        'kind',
        sa.Column('fields', postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text(f"'{ALL}'")),
    )
    for name, groups in DEFAULTS.items():
        op.execute(sa.text("UPDATE kind SET fields = CAST(:groups AS text[]) WHERE name_en = :name").bindparams(groups=groups, name=name))
    op.alter_column('kind', 'fields', server_default=None)


def downgrade() -> None:
    op.drop_column('kind', 'fields')
