"""
Server module for backwards compatibility.
Provides a FastAPI app instance without circular imports.
"""

import importlib.metadata

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .routes import agent_router, auth_router, chat_router, model_router, tool_router

# Get package metadata
try:
    metadata = importlib.metadata.metadata("openagent")
except importlib.metadata.PackageNotFoundError:
    # Default values if package metadata is not available
    metadata = {
        "Summary": "API for OpenAgent",
        "Version": "1.0.0",
        "Author": "RSS3",
        "Author-email": "info@rss3.io",
    }

# Create FastAPI app with metadata
app = FastAPI(
    title="OpenAgent API",
    description=metadata.get("Summary", "API for OpenAgent"),
    version=metadata.get("Version", "1.0.0"),
    contact={
        "name": metadata.get("Author", "RSS3"),
        "url": "https://rss3.io/",
        "email": metadata.get("Author-email", "info@rss3.io"),
    },
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    servers=[
        {
            "url": "http://localhost:8888",
            "description": "Local",
        }
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(agent_router)
app.include_router(model_router)
app.include_router(tool_router)
app.include_router(auth_router)
app.include_router(chat_router)

__all__ = ["app"]
