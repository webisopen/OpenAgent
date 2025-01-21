from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from .routes import agent_router, model_router, tool_router

app = FastAPI(
    title="OpenAgent API",
    description="OpenAgent is an AI agent platform that supports multiple LLM providers and tools.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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
