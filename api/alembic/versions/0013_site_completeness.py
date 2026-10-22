"""profile headline, tag groups, site title/description, updated_at for the "recent updates" feed

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa


revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None

# Tables whose edits show in the public "recent updates" list.
STAMPED = ("project", "article", "work_entry", "education_entry", "profile")


def upgrade() -> None:
    for name in ("headline_th", "headline_en"):
        op.add_column('profile', sa.Column(name, sa.String(200), nullable=False, server_default=""))
        op.alter_column('profile', name, server_default=None)
    for name in ("group_th", "group_en"):
        op.add_column('tag', sa.Column(name, sa.String(60), nullable=False, server_default=""))
        op.alter_column('tag', name, server_default=None)
    for name, size in (("site_title_th", 120), ("site_title_en", 120), ("site_description_th", 300), ("site_description_en", 300)):
        op.add_column('site_settings', sa.Column(name, sa.String(size), nullable=False, server_default=""))
        op.alter_column('site_settings', name, server_default=None)
    # Existing rows stay NULL on purpose: nobody knows when they were last edited, so they stay out of the feed
    # instead of all claiming to be updated on the day of this migration.
    for table in STAMPED:
        op.add_column(table, sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for table in STAMPED:
        op.drop_column(table, 'updated_at')
    for name in ("site_title_th", "site_title_en", "site_description_th", "site_description_en"):
        op.drop_column('site_settings', name)
    for name in ("group_th", "group_en"):
        op.drop_column('tag', name)
    for name in ("headline_th", "headline_en"):
        op.drop_column('profile', name)
