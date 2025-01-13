from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()  # type: ignore


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    personality = Column(String)
    instruction = Column(String)
    wallet_address = Column(String, nullable=False)
    token_image = Column(String)
    ticker = Column(String, nullable=False)
    contract_address = Column(String)
    pair_address = Column(String)
    twitter = Column(String)
    telegram = Column(String)
    website = Column(String)
    type = Column(String, nullable=False)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.UTC, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.UTC, onupdate=datetime.UTC, nullable=False
    )
