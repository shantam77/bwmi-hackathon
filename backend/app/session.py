import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import ENVIRONMENT

SESSION_COOKIE_NAME = "session_id"


class SessionMiddleware(BaseHTTPMiddleware):
    """Issues a session_id cookie on first contact and exposes it as
    request.state.session_id. This is the only identity every table and
    every tool call is keyed by -- no other notion of "user" exists."""

    async def dispatch(self, request: Request, call_next):
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        is_new = session_id is None
        if is_new:
            session_id = str(uuid.uuid4())
        request.state.session_id = session_id

        response = await call_next(request)

        if is_new:
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_id,
                httponly=True,
                secure=ENVIRONMENT == "production",
                samesite="none" if ENVIRONMENT == "production" else "lax",
                max_age=60 * 60 * 24 * 30,
            )
        return response
