"""convert meal_plan_slots from labeled slot to position stack

Revision ID: 67a492d04344
Revises: 1ad2bd1073d6
Create Date: 2026-04-25 13:38:26.283538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67a492d04344'
down_revision: Union[str, None] = '1ad2bd1073d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SLOT_ORDER_SQL = """
    UPDATE meal_plan_slots
    SET position = CASE slot
        WHEN 'breakfast' THEN 0
        WHEN 'lunch'     THEN 1
        WHEN 'dinner'    THEN 2
        WHEN 'extra'     THEN 3
        ELSE 0
    END
"""


def upgrade() -> None:
    # 1. Add position (nullable for now), backfill from old slot labels.
    op.add_column('meal_plan_slots', sa.Column('position', sa.Integer(), nullable=True))
    op.execute(SLOT_ORDER_SQL)
    op.alter_column('meal_plan_slots', 'position', nullable=False)

    # 2. Swap the unique constraint to (slot_date, position) and drop slot.
    op.drop_constraint('uq_meal_plan_slot_date_slot', 'meal_plan_slots', type_='unique')
    op.create_unique_constraint(
        'uq_meal_plan_slot_date_position',
        'meal_plan_slots',
        ['slot_date', 'position'],
    )
    op.drop_column('meal_plan_slots', 'slot')


def downgrade() -> None:
    op.add_column(
        'meal_plan_slots',
        sa.Column('slot', sa.String(length=20), nullable=True),
    )
    # Best-effort reverse mapping; positions beyond 3 collapse to 'extra'.
    op.execute("""
        UPDATE meal_plan_slots
        SET slot = CASE position
            WHEN 0 THEN 'breakfast'
            WHEN 1 THEN 'lunch'
            WHEN 2 THEN 'dinner'
            ELSE        'extra'
        END
    """)
    op.alter_column('meal_plan_slots', 'slot', nullable=False)
    op.drop_constraint('uq_meal_plan_slot_date_position', 'meal_plan_slots', type_='unique')
    op.create_unique_constraint(
        'uq_meal_plan_slot_date_slot',
        'meal_plan_slots',
        ['slot_date', 'slot'],
    )
    op.drop_column('meal_plan_slots', 'position')
