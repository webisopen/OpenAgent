import uvicorn
from dotenv import load_dotenv

from openagent.cache import RedisManager
from openagent.database import DatabaseManager
from openagent.router.server import app


def run():
    load_dotenv()

    # Initialize managers
    DatabaseManager.init()
    RedisManager.init()

    uvicorn.run(app, host="0.0.0.0", reload=False)
