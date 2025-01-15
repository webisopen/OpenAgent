"""create initial tables

Revision ID: 215e5a803b40
Revises:
Create Date: 2025-01-15 12:21:21.782957

"""

from alembic import op
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "215e5a803b40"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequences first
    op.execute("CREATE SEQUENCE models_id_seq")
    op.execute("CREATE SEQUENCE tools_id_seq")
    op.execute("CREATE SEQUENCE agents_id_seq")

    # Create models table
    op.create_table(
        "models",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Sequence("models_id_seq"),
            server_default=sa.text("nextval('models_id_seq')"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capability_score", postgresql.DOUBLE_PRECISION(), nullable=False),
        sa.Column("capabilities", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create tools table
    op.create_table(
        "tools",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Sequence("tools_id_seq"),
            server_default=sa.text("nextval('tools_id_seq')"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "type",
            postgresql.ENUM("text_generation", "social_integration", name="tool_type"),
            nullable=False,
        ),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["models.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create agents table
    op.create_table(
        "agents",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Sequence("agents_id_seq"),
            server_default=sa.text("nextval('agents_id_seq')"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("personality", sa.Text(), nullable=True),
        sa.Column("instruction", sa.Text(), nullable=True),
        sa.Column("wallet_address", sa.String(length=255), nullable=False),
        sa.Column("token_image", sa.String(length=255), nullable=True),
        sa.Column("ticker", sa.String(length=50), nullable=False),
        sa.Column("contract_address", sa.String(length=255), nullable=True),
        sa.Column("pair_address", sa.String(length=255), nullable=True),
        sa.Column("twitter", sa.String(length=255), nullable=True),
        sa.Column("telegram", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("tool_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("inactive", "active", name="agent_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table("agents")
    op.drop_table("tools")
    op.drop_table("models")

    # Drop enum types
    postgresql.ENUM(name="agent_status").drop(op.get_bind())
    postgresql.ENUM(name="tool_type").drop(op.get_bind())
