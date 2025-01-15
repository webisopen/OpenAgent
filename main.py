from dotenv import load_dotenv
import openagent
from openagent.db import init_db

if __name__ == "__main__":
    load_dotenv()

    init_db()

    openagent.run()
