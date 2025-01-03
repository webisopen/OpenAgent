import os
import vertexai
from chainlit.utils import mount_chainlit
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from loguru import logger
from starlette.staticfiles import StaticFiles
import traceback
from starlette.responses import JSONResponse

from openagent.conf.env import settings
from openagent.router import openai_router, widget_router, health_router

load_dotenv()
app = FastAPI(
    title="OpenAgent API",
    description="OpenAgent is a framework for building AI applications leveraging the power of blockchains.",
    license_info={
        "name": "MIT",
        "url": "https://github.com/webisopen/OpenAgent/blob/main/LICENSE",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routers
app.include_router(openai_router)
app.include_router(widget_router)
app.include_router(health_router)

# Check and create static files directory
static_dir = os.path.join("dist", "static")
if not os.path.exists(static_dir):
    try:
        os.makedirs(static_dir)
        logger.info(f"Created directory: {static_dir}")
    except OSError as e:
        logger.error(f"Error creating directory {static_dir}: {e}")

app.mount("/static", StaticFiles(directory=static_dir), name="widget")

mount_chainlit(app=app, target="openagent/ui/app.py", path="")

if settings.VERTEX_PROJECT_ID:
    vertexai.init(project=settings.VERTEX_PROJECT_ID)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Global error: {str(exc)}\nTraceback:\n{traceback.format_exc()}"
    logger.error(error_msg)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "traceback": traceback.format_exc()},
    )


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="OpenAgent API",
        version="1.0.0",
        description="OpenAgent API documentation",
        routes=app.routes,
    )

    openapi_schema["servers"] = [
        {
            "url": "https://agent.open.network",
            "description": "Production server"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
