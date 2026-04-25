"""replace week_menus with meal_plan_slots

Revision ID: 1ad2bd1073d6
Revises: remove_utensils_col
Create Date: 2026-04-25 12:46:48.480676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '1ad2bd1073d6'
down_revision: Union[str, None] = 'remove_utensils_col'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_week_menus_recipe_id', table_name='week_menus')
    op.drop_table('week_menus')

    op.create_table(
        'meal_plan_slots',
        sa.Column('slot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slot_date', sa.Date(), nullable=False),
        sa.Column('slot', sa.String(length=20), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('servings', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.recipe_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('slot_id'),
        sa.UniqueConstraint('slot_date', 'slot', name='uq_meal_plan_slot_date_slot'),
    )
    op.create_index('ix_meal_plan_slots_slot_date', 'meal_plan_slots', ['slot_date'])
    op.create_index('ix_meal_plan_slots_recipe_id', 'meal_plan_slots', ['recipe_id'])


def downgrade() -> None:
    op.drop_index('ix_meal_plan_slots_recipe_id', table_name='meal_plan_slots')
    op.drop_index('ix_meal_plan_slots_slot_date', table_name='meal_plan_slots')
    op.drop_table('meal_plan_slots')

    op.create_table(
        'week_menus',
        sa.Column('menu_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('recipe_name', sa.String(length=255), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('menu_date', sa.DateTime(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.recipe_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('menu_id'),
    )
    op.create_index('ix_week_menus_recipe_id', 'week_menus', ['recipe_id'])
