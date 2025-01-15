from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .routes import chat_router
from openagent.db import get_db

app = FastAPI()


def get_db_session():
    db = get_db()
    try:
        yield db
    finally:
        db.close()


app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
