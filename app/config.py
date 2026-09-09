import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
BREVO_KEY = os.getenv("BRAVO_API_KEY")
UPSTASH_REDIS_REST_URL=os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")
