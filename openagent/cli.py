import asyncio
import os
import signal

import click
from dotenv import load_dotenv

from openagent.core.agent import OpenAgent

load_dotenv()


def handle_signals(loop):
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(loop)))


async def shutdown(loop):
    click.echo("\nShutting down...")
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
def start(file):
    """Start OpenAgent with specified config file"""
    if not os.path.exists(file):
        click.echo(f"Error: Config file '{file}' not found")
        return

    try:
        agent = OpenAgent(file)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        handle_signals(loop)

        loop.create_task(agent.start())
        try:
            loop.run_forever()
        finally:
            loop.close()

    except Exception as e:
        click.echo(f"Error: {e}")


if __name__ == "__main__":
    cli()
