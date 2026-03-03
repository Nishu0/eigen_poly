import urllib.parse
from dotenv import load_dotenv
load_dotenv(dotenv_path='apps/backend/.env')
import os

url = os.environ.get("DATABASE_URL")
if not url:
    print("NO DB URL LOCALLY")
else:
    print(f"URL: {url}")
