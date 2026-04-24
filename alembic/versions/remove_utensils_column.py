"""remove utensils column

Revision ID: remove_utensils_col
Revises: 014bfbf7c55d
Create Date: 2026-01-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'remove_utensils_col'
down_revision = '014bfbf7c55d'
branch_labels = None
depends_on = None


def upgrade():
    # Remove utensils column from recipes table
    op.drop_column('recipes', 'utensils')


def downgrade():
    # Add back utensils column if rollback is needed
    op.add_column('recipes', sa.Column('utensils', postgresql.ARRAY(sa.String()), nullable=True))
