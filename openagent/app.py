from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .router.openai import router as openai_router

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