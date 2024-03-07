from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from copilot.conf.env import settings
from copilot.db.models import Base

engine = create_engine(
    settings.postgres_connection_string(), connect_args={"options": "-c timezone=utc"}
)
Base.metadata.create_all(bind=engine)  # type: ignore

DBSession = sessionmaker(bind=engine)
