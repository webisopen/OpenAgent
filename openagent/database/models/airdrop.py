import enum
from openagent.database.models.base import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    UniqueConstraint,
    DateTime,
    Enum,
    Boolean,
    Float,
)
from datetime import UTC, datetime


class AirdropStatus(enum.Enum):
    ELIGIBLE = "eligible"  # Eligible
    NOT_ELIGIBLE = "not_eligible"  # Not eligible
    SENT = "sent"  # Airdrop sent


class AirdropEligibility(Base):
    """Wallet airdrop eligibility and data table"""

    __tablename__ = "airdrop_eligibility"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, nullable=False)
    wallet_address = Column(String, nullable=False)
    contract_address = Column(String, nullable=False)
    chain_id = Column(Integer, nullable=False)

    airdrop_status = Column(
        Enum(AirdropStatus), nullable=False, default=AirdropStatus.NOT_ELIGIBLE
    )
    score = Column(Float)  # score , calc from bruce
    ai_multiplier = Column(
        Float, default=1.0
    )  # AI interaction multiplier n, where 1 ≤ n ≤ n_max
    random_factor = Column(Float, default=1.0)  # Random factor r, where 0.95 ≤ r ≤ 1.05
    amount = Column(Integer)  # Final airdrop amount, stored as integer
    is_persuaded = Column(
        Boolean, default=False
    )  # True if user has convinced AI @twitter
    daily_attempts = Column(
        Integer, default=0
    )  # Number of persuasion attempts today @twitter
    last_attempt_date = Column(DateTime)  # Last persuasion attempt date @twitter

    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "agent_id", "wallet_address", "contract_address", name="wallet_ca_idx"
        ),
    )


class AirdropDistribution(Base):
    """Records all airdrop history for users"""

    __tablename__ = "airdrop_distribution"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, nullable=False)
    wallet_address = Column(String, nullable=False)
    token_address = Column(
        String, nullable=False
    )  # Contract address of the airdropped token
    amount = Column(Integer, nullable=False)  # Airdrop amount stored as integer
    airdrop_time = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Add index to improve query performance
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "wallet_address",
            "token_address",
            "airdrop_time",
            name="unique_airdrop_record",
        ),
    )
