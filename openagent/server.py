import uvicorn
from openagent.router.server import app
from openagent.database import DatabaseManager
from openagent.cache import RedisManager
from dotenv import load_dotenv


def run():
    load_dotenv()

    # Initialize managers
    DatabaseManager.init()
    RedisManager.init()

    uvicorn.run(app, host="0.0.0.0", reload=False)
