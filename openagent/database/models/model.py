from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from openagent.database.models.base import Base
from datetime import datetime, UTC


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    capability_score = Column(Float, nullable=False)  # Model capability score
    capabilities = Column(
        String
    )  # Stores ModelCapability list as comma-separated string
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
