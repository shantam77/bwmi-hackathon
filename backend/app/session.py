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

        # A route handler (e.g. POST /api/session/new) may have already set
        # its own session_id cookie on this response -- don't clobber it
        # with the fallback ID generated above just because the *incoming*
        # request had no cookie yet. Only reachable in practice if a route
        # ever issues a fresh session before any cookie exists at all, but
        # trusting request ordering here would be fragile.
        already_set = any(
            header.split("=", 1)[0] == SESSION_COOKIE_NAME
            for header in response.headers.getlist("set-cookie")
        )
        if is_new and not already_set:
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_id,
                httponly=True,
                secure=ENVIRONMENT == "production",
                samesite="none" if ENVIRONMENT == "production" else "lax",
                max_age=60 * 60 * 24 * 30,
            )
        return response
