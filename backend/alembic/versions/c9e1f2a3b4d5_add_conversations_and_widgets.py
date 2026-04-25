"""add conversations and workspace_widgets tables

Revision ID: c9e1f2a3b4d5
Revises: a3f9c2d1e4b7
Create Date: 2026-04-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e1f2a3b4d5"
down_revision: Union[str, Sequence[str], None] = "a3f9c2d1e4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("business_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("messages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_business_user", "conversations", ["business_id", "user_id"])

    op.create_table(
        "workspace_widgets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("business_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("widget_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_widgets_business_user", "workspace_widgets", ["business_id", "user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_widgets_business_user", table_name="workspace_widgets")
    op.drop_table("workspace_widgets")
    op.drop_index("ix_conversations_business_user", table_name="conversations")
    op.drop_table("conversations")
