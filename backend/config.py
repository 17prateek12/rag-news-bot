import os
from dotenv import load_dotenv
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
REDIS_URL = os.getenv("REDIS_URL")
JINA_API_KEY = os.getenv("JINA_API_KEY")
QDRANT_API = os.getenv("QDRANT_API")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
POSTGRES_URL = os.getenv("POSTGRES_URL")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DECODE = os.getenv("REDIS_DECODE_RESPONSES")
REDIS_USERNAME = os.getenv("REDIS_Username")