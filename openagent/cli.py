import asyncio
import os
import signal
import sys
from typing import Optional
import click
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openagent.agent.agent import OpenAgent

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))

# Create FastAPI app
app = FastAPI(title="OpenAgent API", description="API for OpenAgent", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store agent instance with type hint
agent_instance: Optional[OpenAgent] = None


class ChatRequest(BaseModel):
    message: str


# Test endpoint
@app.get("/test")
async def test():
    return {"status": "ok", "message": "OpenAgent API is running"}


# Chat endpoint
@app.post("/chat")
async def chat(request: ChatRequest):
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    try:
        response = await agent_instance.chat(request.message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def win_handler(signum, frame):
    sys.exit()


async def shutdown(agent, loop):
    click.echo("\nShutting down...")
    agent.stop()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


@click.group()
def cli():
    """OpenAgent CLI tool"""
    pass


@cli.command()
@click.option("-f", "--file", required=True, help="Path to the config file")
@click.option("--host", default="0.0.0.0", help="Host to bind the API server")
@click.option("--port", default=8000, help="Port to bind the API server")
def start(file, host, port):
    """Start OpenAgent with specified config file"""
    if not os.path.exists(file):
        click.echo(f"Error: Config file '{file}' not found")
        return

    global agent_instance
    agent_instance = OpenAgent.from_yaml_file(file)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if sys.platform == "win32":
        signal.signal(signal.SIGINT, win_handler)
    else:
        loop.add_signal_handler(
            signal.SIGINT, lambda: asyncio.create_task(shutdown(agent_instance, loop))
        )
        loop.add_signal_handler(
            signal.SIGTERM, lambda: asyncio.create_task(shutdown(agent_instance, loop))
        )

    # Create FastAPI config
    config = uvicorn.Config(app, host=host, port=port, loop=loop)
    server = uvicorn.Server(config)

    # Run both FastAPI and OpenAgent
    loop.create_task(agent_instance.start())
    loop.create_task(server.serve())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown(agent_instance, loop))
    finally:
        loop.close()


if __name__ == "__main__":
    cli()
