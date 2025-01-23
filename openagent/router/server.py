import importlib.metadata

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .routes import agent_router, auth_router, model_router, tool_router

metadata = importlib.metadata.metadata("openagent")

app = FastAPI(
    title="OpenAgent API",
    description=metadata["Summary"],
    version=metadata["Version"],
    contact={
        "name": metadata["Author"],
        "url": "https://rss3.io/",
        "email": metadata["Author-email"],
    },
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    servers=(
        [
            {
                "url": "http://localhost:8000",
                "description": "Local",
            },
            {
                "url": "https://openagent-oa-141022883942.us-central1.run.app",
                "description": "Development",
            },
        ]
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(model_router)
app.include_router(tool_router)
app.include_router(auth_router)
