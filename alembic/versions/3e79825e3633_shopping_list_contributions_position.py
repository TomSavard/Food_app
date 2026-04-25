"""shopping_list contributions + position

Revision ID: 3e79825e3633
Revises: 67a492d04344
Create Date: 2026-04-25 21:19:19.202314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '3e79825e3633'
down_revision: Union[str, None] = '67a492d04344'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create contributions table.
    op.create_table(
        'shopping_list_contributions',
        sa.Column('contribution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity_text', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('source_label', sa.String(length=255), nullable=False, server_default='Manuel'),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('slot_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['shopping_list.item_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.recipe_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['slot_id'], ['meal_plan_slots.slot_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('contribution_id'),
    )
    op.create_index('ix_shopping_list_contributions_item_id', 'shopping_list_contributions', ['item_id'])
    op.create_index('ix_shopping_list_contributions_slot_id', 'shopping_list_contributions', ['slot_id'])

    # 2. Add position column (nullable for backfill).
    op.add_column('shopping_list', sa.Column('position', sa.Integer(), nullable=True))

    # 3. Backfill: one contribution per existing item, position by created_at within (is_checked).
    op.execute("""
        INSERT INTO shopping_list_contributions
            (contribution_id, item_id, quantity_text, source_label, created_at)
        SELECT
            gen_random_uuid(), item_id,
            COALESCE(quantity, ''),
            COALESCE(NULLIF(source, ''), 'Manuel'),
            NOW()
        FROM shopping_list
    """)
    op.execute("""
        WITH ranked AS (
            SELECT item_id,
                   (ROW_NUMBER() OVER (PARTITION BY is_checked ORDER BY created_at) - 1)
                   + (CASE WHEN is_checked THEN 100000 ELSE 0 END) AS rn
            FROM shopping_list
        )
        UPDATE shopping_list s
        SET position = r.rn
        FROM ranked r
        WHERE s.item_id = r.item_id
    """)

    op.alter_column('shopping_list', 'position', nullable=False, server_default='0')

    # 4. Drop old columns.
    op.drop_column('shopping_list', 'quantity')
    op.drop_column('shopping_list', 'source')


def downgrade() -> None:
    op.add_column('shopping_list', sa.Column('quantity', sa.String(length=100), nullable=True, server_default=''))
    op.add_column('shopping_list', sa.Column('source', sa.String(length=500), nullable=True, server_default=''))

    # Best-effort restore: concatenate all contributions per item.
    op.execute("""
        UPDATE shopping_list s SET
            quantity = COALESCE((
                SELECT string_agg(c.quantity_text, ' + ' ORDER BY c.created_at)
                FROM shopping_list_contributions c WHERE c.item_id = s.item_id
            ), ''),
            source = COALESCE((
                SELECT string_agg(c.source_label, ', ' ORDER BY c.created_at)
                FROM shopping_list_contributions c WHERE c.item_id = s.item_id
            ), '')
    """)

    op.alter_column('shopping_list', 'quantity', nullable=False)
    op.alter_column('shopping_list', 'source', nullable=False)
    op.drop_column('shopping_list', 'position')

    op.drop_index('ix_shopping_list_contributions_slot_id', table_name='shopping_list_contributions')
    op.drop_index('ix_shopping_list_contributions_item_id', table_name='shopping_list_contributions')
    op.drop_table('shopping_list_contributions')
