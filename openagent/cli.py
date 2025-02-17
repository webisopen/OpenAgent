import asyncio
import os
import signal
import sys
import click
from dotenv import load_dotenv

from openagent.agent.agent import OpenAgent

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))


def win_handler(signum, frame):
    sys.exit()


async def shutdown(agent, loop):
    click.echo("\nShutting down...")
    agent.stop_scheduler()
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

    agent = OpenAgent.from_yaml_file(file)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if sys.platform == "win32":
        signal.signal(signal.SIGINT, win_handler)
    else:
        loop.add_signal_handler(
            signal.SIGINT, lambda: asyncio.create_task(shutdown(agent, loop))
        )
        loop.add_signal_handler(
            signal.SIGTERM, lambda: asyncio.create_task(shutdown(agent, loop))
        )

    loop.create_task(agent.start())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown(agent, loop))
    finally:
        loop.close()


if __name__ == "__main__":
    cli()
