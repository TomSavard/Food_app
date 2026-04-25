"""ingredient match (FK), aliases, modified flag, density

Revision ID: 2a4c1f9b8d3e
Revises: 1ff96d7db0d7
Create Date: 2026-04-25 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "2a4c1f9b8d3e"
down_revision: Union[str, None] = "1ff96d7db0d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Trigram similarity for the LLM candidate pre-filter.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ingredient_database: track curation + density.
    op.add_column(
        "ingredient_database",
        sa.Column("modified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "ingredient_database",
        sa.Column("modified_by", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "ingredient_database",
        sa.Column("modified_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "ingredient_database",
        sa.Column("density_g_per_ml", sa.Float(), nullable=True),
    )

    # Trigram index on alim_nom_fr for the candidate pre-filter.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ingredient_database_name_trgm "
        "ON ingredient_database USING gin (alim_nom_fr gin_trgm_ops)"
    )

    # ingredient_aliases: persisted fuzzy-match outcomes.
    op.create_table(
        "ingredient_aliases",
        sa.Column(
            "alias_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "ingredient_db_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingredient_database.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("alias_text", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_ingredient_aliases_alias_text_lower "
        "ON ingredient_aliases (LOWER(alias_text))"
    )
    op.execute(
        "CREATE INDEX ix_ingredient_aliases_alias_text_trgm "
        "ON ingredient_aliases USING gin (alias_text gin_trgm_ops)"
    )

    # FK from recipe ingredients → knowledge base.
    op.add_column(
        "ingredients",
        sa.Column(
            "ingredient_db_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingredient_database.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_ingredients_ingredient_db_id", "ingredients", ["ingredient_db_id"]
    )

    # FK from shopping list items → knowledge base.
    op.add_column(
        "shopping_list",
        sa.Column(
            "ingredient_db_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingredient_database.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_shopping_list_ingredient_db_id", "shopping_list", ["ingredient_db_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_shopping_list_ingredient_db_id", table_name="shopping_list")
    op.drop_column("shopping_list", "ingredient_db_id")

    op.drop_index("ix_ingredients_ingredient_db_id", table_name="ingredients")
    op.drop_column("ingredients", "ingredient_db_id")

    op.execute("DROP INDEX IF EXISTS ix_ingredient_aliases_alias_text_trgm")
    op.execute("DROP INDEX IF EXISTS uq_ingredient_aliases_alias_text_lower")
    op.drop_table("ingredient_aliases")

    op.execute("DROP INDEX IF EXISTS ix_ingredient_database_name_trgm")
    op.drop_column("ingredient_database", "density_g_per_ml")
    op.drop_column("ingredient_database", "modified_at")
    op.drop_column("ingredient_database", "modified_by")
    op.drop_column("ingredient_database", "modified")
    # pg_trgm extension is left in place — harmless.
