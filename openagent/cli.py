import asyncio
import os
import click
import uvicorn

from dotenv import load_dotenv
from openagent.agent.agent import OpenAgent
from openagent.api.app import app, set_agent

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))


def shutdown():
    click.echo("\nShutting down...")
    os._exit(0)


@click.group()
def cli():
    """OpenAgent CLI tool"""
    pass


@cli.command()
@click.option("-f", "--file", required=True, help="Path to the config file")
@click.option("--host", default="0.0.0.0", help="Host to bind the API server")
@click.option("--port", default=8888, help="Port to bind the API server")
def start(file, host, port):
    """Start OpenAgent with specified config file"""
    if not os.path.exists(file):
        click.echo(f"Error: Config file '{file}' not found")
        return

    agent = OpenAgent.from_yaml_file(file)
    set_agent(agent)  # Set the agent instance for the API

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Create FastAPI config
    config = uvicorn.Config(app, host=host, port=port)
    server = uvicorn.Server(config)

    # Run both FastAPI and OpenAgent
    loop.create_task(agent.start())
    loop.create_task(server.serve())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown())
    finally:
        loop.close()


if __name__ == "__main__":
    cli()
