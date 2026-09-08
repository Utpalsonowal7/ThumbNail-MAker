import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
BREVO_KEY = os.getenv("BRAVO_API_KEY")
