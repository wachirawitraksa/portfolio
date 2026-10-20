"""profile, contact links and site settings

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    profile = op.create_table('profile',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name_th', sa.String(length=120), nullable=False),
    sa.Column('name_en', sa.String(length=120), nullable=False),
    sa.Column('intro_th', sa.Text(), nullable=False),
    sa.Column('intro_en', sa.Text(), nullable=False),
    sa.Column('location_th', sa.String(length=200), nullable=False),
    sa.Column('location_en', sa.String(length=200), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('photo_key', sa.String(length=200), nullable=False),
    sa.Column('photo_content_type', sa.String(length=50), nullable=False),
    sa.Column('cv_th_key', sa.String(length=200), nullable=False),
    sa.Column('cv_th_name', sa.String(length=200), nullable=False),
    sa.Column('cv_en_key', sa.String(length=200), nullable=False),
    sa.Column('cv_en_name', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('contact_link',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('label', sa.String(length=80), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    settings = op.create_table('site_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('featured_limit', sa.Integer(), nullable=False),
    sa.Column('projects_page_size', sa.Integer(), nullable=False),
    sa.Column('articles_page_size', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    empty = {c: "" for c in (
        'name_th', 'name_en', 'intro_th', 'intro_en', 'location_th', 'location_en', 'email',
        'photo_key', 'photo_content_type', 'cv_th_key', 'cv_th_name', 'cv_en_key', 'cv_en_name',
    )}
    op.bulk_insert(profile, [{"id": 1, **empty}])
    op.bulk_insert(settings, [{"id": 1, "featured_limit": 6, "projects_page_size": 12, "articles_page_size": 12}])


def downgrade() -> None:
    op.drop_table('site_settings')
    op.drop_table('contact_link')
    op.drop_table('profile')
