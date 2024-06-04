import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
API_TOKEN = (os.getenv("API_TOKEN"))

# URL Базы данных
DATABASE_URL = (os.getenv("DATABASE_URL"))

# URL MANIFEST TON
MANIFEST_URL = (os.getenv("MANIFEST_URL"))