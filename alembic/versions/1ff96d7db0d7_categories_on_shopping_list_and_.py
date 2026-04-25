"""categories on shopping_list and ingredient_database

Revision ID: 1ff96d7db0d7
Revises: 3e79825e3633
Create Date: 2026-04-25 21:53:39.837335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ff96d7db0d7'
down_revision: Union[str, None] = '3e79825e3633'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ingredient_database: knowledge that survives CIQUAL re-imports.
    # 'category' is what heuristic + LLM + user corrections converge on.
    # 'source' tracks origin so a future re-import can safely overwrite
    # ciqual rows but never user-corrected ones.
    op.add_column(
        'ingredient_database',
        sa.Column('category', sa.String(length=50), nullable=True),
    )
    op.add_column(
        'ingredient_database',
        sa.Column('source', sa.String(length=20), nullable=False, server_default='ciqual'),
    )
    op.create_index('ix_ingredient_database_category', 'ingredient_database', ['category'])

    # shopping_list: the resolved category for this ingredient on the list.
    # NULL means not yet categorized; the next mutation will set it.
    op.add_column(
        'shopping_list',
        sa.Column('category', sa.String(length=50), nullable=True),
    )
    op.create_index('ix_shopping_list_category', 'shopping_list', ['category'])


def downgrade() -> None:
    op.drop_index('ix_shopping_list_category', table_name='shopping_list')
    op.drop_column('shopping_list', 'category')
    op.drop_index('ix_ingredient_database_category', table_name='ingredient_database')
    op.drop_column('ingredient_database', 'source')
    op.drop_column('ingredient_database', 'category')
