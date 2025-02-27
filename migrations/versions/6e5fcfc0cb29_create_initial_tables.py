"""create initial tables

Revision ID: 6e5fcfc0cb29
Revises:
Create Date: 2025-02-27 16:37:55.184916

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6e5fcfc0cb29"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if we're using SQLite - prefix with _ to indicate intentionally unused
    _is_sqlite = op.get_context().dialect.name == "sqlite"

    # SQLite-specific workarounds can be added here if needed

    # Create models table
    op.create_table(
        "models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("capability_score", sa.Float(), nullable=False),
        sa.Column("capabilities", sa.String()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    # Create tools table
    op.create_table(
        "tools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    # Create agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.String()),
        sa.Column("personality", sa.String()),
        sa.Column("instruction", sa.String()),
        sa.Column("wallet_address", sa.String(), nullable=False),
        sa.Column("token_image", sa.String()),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("contract_address", sa.String()),
        sa.Column("pair_address", sa.String()),
        sa.Column("twitter", sa.String()),
        sa.Column("telegram", sa.String()),
        sa.Column("website", sa.String()),
        sa.Column("tool_configs", sa.Text()),  # JSON as text for SQLite
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    # Check if we're using SQLite - prefix with _ to indicate intentionally unused
    _is_sqlite = op.get_context().dialect.name == "sqlite"

    # SQLite-specific workarounds can be added here if needed

    # Drop all tables
    op.drop_table("agents")
    op.drop_table("tools")
    op.drop_table("models")
