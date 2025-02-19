import asyncio
import os
import signal
import sys
import click
import uvicorn
import threading
import time

from dotenv import load_dotenv
from openagent.agent.agent import OpenAgent
from openagent.api.app import app, set_agent

load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))


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


def check_exit_windows(loop):
    """Check for exit command on Windows (press 'q' to quit)"""
    import msvcrt

    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode("utf-8").lower()
            if key == "q":
                print("\nShutting down...")
                os._exit(0)  # Force exit
        time.sleep(1)


def check_exit_unix(loop):
    """Check for exit command on Unix (press 'q' to quit)"""
    print("\nPress 'q' to quit...")
    while True:
        try:
            # Non-blocking read from stdin
            import select

            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1)
                if key == "q":
                    print("\nShutting down...")
                    os._exit(0)
        except Exception as e:
            print(f"Error reading input: {e}")
        time.sleep(1)


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

    # Set platform specific handlers
    if sys.platform == "win32":
        signal.signal(signal.SIGINT, win_handler)
        check_exit_func = check_exit_windows
    else:
        loop.add_signal_handler(
            signal.SIGINT, lambda: asyncio.create_task(shutdown(agent, loop))
        )
        loop.add_signal_handler(
            signal.SIGTERM, lambda: asyncio.create_task(shutdown(agent, loop))
        )
        check_exit_func = check_exit_unix

    # Create FastAPI config
    config = uvicorn.Config(app, host=host, port=port, loop=loop)
    server = uvicorn.Server(config)

    # Run both FastAPI and OpenAgent
    loop.create_task(agent.start())
    loop.create_task(server.serve())

    # Start exit command checker in a separate thread
    exit_thread = threading.Thread(target=check_exit_func, args=(loop,), daemon=True)
    exit_thread.start()

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown(agent, loop))
    finally:
        loop.close()


if __name__ == "__main__":
    cli()
