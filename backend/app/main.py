from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import DATABASE_URL, FRONTEND_ORIGIN
from app.db import init_db
from app.routers import chat, clock as clock_router, session as session_router
from app.session import SessionMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_URL:
        init_db()
    yield


app = FastAPI(title="Saarthi backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware)

app.include_router(chat.router)
app.include_router(session_router.router)
app.include_router(clock_router.router)


@app.get("/api/health")
def health(request: Request):
    return {"status": "ok", "session_id": request.state.session_id}
