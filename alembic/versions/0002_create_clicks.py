"""create clicks table

Revision ID: 0002_create_clicks
Revises: 0001_create_links
Create Date: 2026-10-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_create_clicks"
down_revision: Union[str, None] = "0001_create_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clicks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device", sa.String(length=20), nullable=False),
        sa.Column("browser", sa.String(length=50), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["link_id"], ["links.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clicks_link_id"), "clicks", ["link_id"], unique=False)
    op.create_index(op.f("ix_clicks_clicked_at"), "clicks", ["clicked_at"], unique=False)
    op.create_index(
        "ix_clicks_link_id_clicked_at", "clicks", ["link_id", "clicked_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_clicks_link_id_clicked_at", table_name="clicks")
    op.drop_index(op.f("ix_clicks_clicked_at"), table_name="clicks")
    op.drop_index(op.f("ix_clicks_link_id"), table_name="clicks")
    op.drop_table("clicks")
