import os

from dotenv import load_dotenv

load_dotenv()

def _normalize_database_url(raw: str) -> str:
    """Railway (and most providers) hand out postgresql:// or the legacy
    postgres://. We install psycopg (v3), so SQLAlchemy needs the dialect
    spelled out explicitly, or it defaults to the psycopg2 driver we don't
    have installed."""
    if not raw:
        return raw
    if raw.startswith("postgresql+"):
        return raw
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+psycopg://", 1)
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql+psycopg://", 1)
    return raw


DATABASE_URL = _normalize_database_url(os.environ.get("DATABASE_URL", ""))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# The project's OpenAI API key is restricted to exactly this model -- every
# other model is blocked at the key level. Do not change this without
# confirming the key's allowed-model list first.
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini-2025-08-07")

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

# "production" (Vercel <-> Railway, cross-origin) needs SameSite=None; Secure,
# which only works over HTTPS. "development" (localhost <-> localhost) relaxes
# both so the session cookie still round-trips over plain HTTP.
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# Gates POST /api/admin/reset-db (wipes all demo data across every session --
# see app/routers/admin.py). Unset by default so the endpoint refuses rather
# than silently allowing an empty-token bypass once this is deployed publicly.
ADMIN_RESET_TOKEN = os.environ.get("ADMIN_RESET_TOKEN", "")
