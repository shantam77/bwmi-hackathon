import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

# "production" (Vercel <-> Railway, cross-origin) needs SameSite=None; Secure,
# which only works over HTTPS. "development" (localhost <-> localhost) relaxes
# both so the session cookie still round-trips over plain HTTP.
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
