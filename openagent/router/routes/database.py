from openagent.db import get_db


def get_db_session():
    db = get_db()
    try:
        yield db
    finally:
        db.close()
