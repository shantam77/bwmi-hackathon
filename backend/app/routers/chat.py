from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.runner import stream_chat

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/api/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    session_id = request.state.session_id
    return StreamingResponse(
        stream_chat(session_id, body.message),
        media_type="text/event-stream",
    )
