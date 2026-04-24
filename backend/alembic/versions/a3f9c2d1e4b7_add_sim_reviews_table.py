"""add sim_reviews table for living demo world

Revision ID: a3f9c2d1e4b7
Revises: e273fafbe8de
Create Date: 2026-04-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3f9c2d1e4b7"
down_revision: Union[str, Sequence[str], None] = "e273fafbe8de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sim_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("place_id", sa.String(255), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id", "external_id", name="uq_sim_reviews_place_ext"),
    )
    op.create_index("ix_sim_reviews_place_id", "sim_reviews", ["place_id"])


def downgrade() -> None:
    op.drop_index("ix_sim_reviews_place_id", "sim_reviews")
    op.drop_table("sim_reviews")
