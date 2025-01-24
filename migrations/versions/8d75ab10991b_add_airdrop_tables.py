"""add_airdrop_tables

Revision ID: 8d75ab10991b
Revises: 215e5a803b40
Create Date: 2025-01-24 18:20:29.984134

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8d75ab10991b"
down_revision: Union[str, None] = "215e5a803b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequences first
    op.execute("CREATE SEQUENCE airdrop_eligibility_id_seq")
    op.execute("CREATE SEQUENCE airdrop_distribution_id_seq")

    # Create airdrop_eligibility table
    op.create_table(
        "airdrop_eligibility",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Sequence("airdrop_eligibility_id_seq"),
            server_default=sa.text("nextval('airdrop_eligibility_id_seq')"),
            nullable=False,
        ),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("wallet_address", sa.String(), nullable=False),
        sa.Column("contract_address", sa.String(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column(
            "airdrop_status",
            postgresql.ENUM("eligible", "not_eligible", "sent", name="airdrop_status"),
            nullable=False,
            index=True,
            server_default="not_eligible",
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("ai_multiplier", sa.Float(), server_default="1.0"),
        sa.Column("random_factor", sa.Float(), server_default="1.0"),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("is_persuaded", sa.Boolean(), server_default="false"),
        sa.Column("daily_attempts", sa.Integer(), server_default="0"),
        sa.Column(
            "last_attempt_date", postgresql.TIMESTAMP(timezone=True), nullable=True
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
        sa.UniqueConstraint(
            "agent_id", "wallet_address", "contract_address", name="wallet_ca_idx"
        ),
    )

    # Create airdrop_distribution table
    op.create_table(
        "airdrop_distribution",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Sequence("airdrop_distribution_id_seq"),
            server_default=sa.text("nextval('airdrop_distribution_id_seq')"),
            nullable=False,
        ),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("wallet_address", sa.String(), nullable=False),
        sa.Column("token_address", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column(
            "airdrop_time",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_id",
            "wallet_address",
            "token_address",
            "airdrop_time",
            name="unique_airdrop_record",
        ),
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table("airdrop_distribution")
    op.drop_table("airdrop_eligibility")

    # Drop enum type
    op.execute("DROP TYPE airdrop_status")

    # Drop sequences
    op.execute("DROP SEQUENCE airdrop_eligibility_id_seq")
    op.execute("DROP SEQUENCE airdrop_distribution_id_seq")
