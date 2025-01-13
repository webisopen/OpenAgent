from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()  # type: ignore


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    capability_score = Column(Float, nullable=False)  # Model capability score
    capabilities = Column(
        String
    )  # Stores ModelCapability list as comma-separated string
    created_at = Column(DateTime, default=datetime.UTC, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.UTC, onupdate=datetime.UTC, nullable=False
    )
