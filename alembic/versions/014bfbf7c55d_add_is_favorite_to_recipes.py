"""add_is_favorite_to_recipes

Revision ID: 014bfbf7c55d
Revises: e8bfb2d4cc50
Create Date: 2026-01-18 12:16:48.133498

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '014bfbf7c55d'
down_revision: Union[str, None] = 'e8bfb2d4cc50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_favorite column to recipes table
    op.add_column('recipes', sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'))
    # Create index on is_favorite for better query performance
    op.create_index(op.f('ix_recipes_is_favorite'), 'recipes', ['is_favorite'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index and column
    op.drop_index(op.f('ix_recipes_is_favorite'), table_name='recipes')
    op.drop_column('recipes', 'is_favorite')
