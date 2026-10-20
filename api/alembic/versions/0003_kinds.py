"""kinds, and generic certificate fields on project

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

DEFAULT_KINDS = (
    ("ผลงาน", "Project"),
    ("ใบเซอร์ / ใบรับรอง", "Certificate"),
    ("รางวัล", "Award"),
    ("คอร์ส", "Course"),
    ("กิจกรรม", "Activity"),
)


def upgrade() -> None:
    kind = op.create_table('kind',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name_th', sa.String(length=120), nullable=False),
    sa.Column('name_en', sa.String(length=120), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('hidden', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.bulk_insert(kind, [
        {"name_th": th, "name_en": en, "sort_order": n, "hidden": False}
        for n, (th, en) in enumerate(DEFAULT_KINDS, start=1)
    ])
    op.add_column('project', sa.Column('kind_id', sa.Integer(), nullable=True))
    op.add_column('project', sa.Column('issuer', sa.String(length=200), nullable=False, server_default=''))
    op.add_column('project', sa.Column('issued_on', sa.Date(), nullable=True))
    op.add_column('project', sa.Column('verify_url', sa.String(length=500), nullable=False, server_default=''))
    op.alter_column('project', 'issuer', server_default=None)
    op.alter_column('project', 'verify_url', server_default=None)
    op.create_foreign_key('project_kind_id_fkey', 'project', 'kind', ['kind_id'], ['id'], ondelete='RESTRICT')
    # Entries that existed before kinds were projects.
    op.execute("UPDATE project SET kind_id = (SELECT id FROM kind ORDER BY sort_order, id LIMIT 1)")


def downgrade() -> None:
    op.drop_constraint('project_kind_id_fkey', 'project', type_='foreignkey')
    op.drop_column('project', 'verify_url')
    op.drop_column('project', 'issued_on')
    op.drop_column('project', 'issuer')
    op.drop_column('project', 'kind_id')
    op.drop_table('kind')
