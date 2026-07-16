"""
Chat — talk to your second brain. Every reply is grounded in your persisted
memory and conversation history, produced entirely by the LOCAL brain.
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_owner
from app.brain.cognition import Cognition
from app.brain.engine import BrainUnavailable
from app.core.di import get_cognition
from app.db.database import get_db
from app.models.models import Conversation, Owner

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    conversation_id: str | None = None
    device_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    owner: Owner = Depends(get_current_owner),
    cognition: Cognition = Depends(get_cognition),
    db: Session = Depends(get_db),
):
    try:
        reply, conv_id = await cognition.respond(
            db, owner.id, body.message, body.conversation_id, body.device_id
        )
        return ChatResponse(reply=reply, conversation_id=conv_id)
    except BrainUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    owner: Owner = Depends(get_current_owner),
    cognition: Cognition = Depends(get_cognition),
    db: Session = Depends(get_db),
):
    async def sse():
        try:
            async for event in cognition.respond_stream(
                db, owner.id, body.message, body.conversation_id, body.device_id
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except BrainUnavailable as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@router.get("/conversations")
async def list_conversations(
    limit: int = 30,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    convs = (
        db.query(Conversation)
        .filter(Conversation.owner_id == owner.id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": c.id, "title": c.title,
            "updated_at": c.updated_at, "message_count": len(c.messages),
        }
        for c in convs
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    owner: Owner = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id, Conversation.owner_id == owner.id
    ).first()
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada")
    return {
        "id": conv.id, "title": conv.title,
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in conv.messages
        ],
    }
