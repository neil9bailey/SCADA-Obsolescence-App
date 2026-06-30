"""add asset source workbook fields

Revision ID: 9f7d2c8a6b31
Revises: f2e35d38f616
Create Date: 2026-06-30 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f7d2c8a6b31"
down_revision: Union[str, Sequence[str], None] = "f2e35d38f616"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_workbook", sa.String(length=260), nullable=True))
        batch_op.add_column(sa.Column("source_sheet", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("source_row", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("source_category", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("source_subcategory", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("source_payload", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("source_formulas", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("source_intelligence", sa.JSON(), nullable=True))
        batch_op.create_index(batch_op.f("ix_assets_source_category"), ["source_category"], unique=False)
        batch_op.create_index(batch_op.f("ix_assets_source_row"), ["source_row"], unique=False)
        batch_op.create_index(batch_op.f("ix_assets_source_subcategory"), ["source_subcategory"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_assets_source_subcategory"))
        batch_op.drop_index(batch_op.f("ix_assets_source_row"))
        batch_op.drop_index(batch_op.f("ix_assets_source_category"))
        batch_op.drop_column("source_intelligence")
        batch_op.drop_column("source_formulas")
        batch_op.drop_column("source_payload")
        batch_op.drop_column("source_subcategory")
        batch_op.drop_column("source_category")
        batch_op.drop_column("source_row")
        batch_op.drop_column("source_sheet")
        batch_op.drop_column("source_workbook")
