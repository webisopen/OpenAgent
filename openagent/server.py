import uvicorn
from openagent.router.server import app
from openagent.db import init_db
from dotenv import load_dotenv


def run():
    load_dotenv()
    init_db()

    uvicorn.run(app, host="0.0.0.0", reload=False)
