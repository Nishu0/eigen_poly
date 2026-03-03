from dotenv import load_dotenv
load_dotenv()
import os, asyncio
from lib.database import init_db

async def test():
    await init_db()
    print("DB initialized")

asyncio.run(test())
