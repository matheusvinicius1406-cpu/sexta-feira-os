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
from app.core.di import get_cognition, get_voice
from app.db.database import get_db
from app.models.models import Conversation, Owner
from app.voice.box import VoiceBox

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    conversation_id: str | None = None
    device_id: str | None = None
    # Base64 (with or without a data: prefix). The brain sees these itself —
    # there is no separate vision model to hand them to any more.
    #
    # Capped at four: each image is prefill the CPU pays before the first token,
    # and an uncapped list is a way to make your own assistant hang for the rest
    # of the afternoon with one request.
    images: list[str] | None = Field(default=None, max_length=4)


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


def _seen(body: ChatRequest) -> list[str] | None:
    """Normalize incoming images to what the model expects, or explain why not.

    Same resize and re-encode as the /vision endpoints, so a photo costs the
    same whichever door it comes through. A picture that cannot be decoded is a
    400 here rather than an obscure failure inside Ollama later.
    """
    if not body.images:
        return None
    from app.brain.vision import prepare_image

    try:
        return [prepare_image(img) for img in body.images]
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Imagem inválida: {e}") from e


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    owner: Owner = Depends(get_current_owner),
    cognition: Cognition = Depends(get_cognition),
    voice: VoiceBox = Depends(get_voice),
    db: Session = Depends(get_db),
):
    try:
        reply, conv_id = await cognition.respond(
            db, owner.id, body.message, body.conversation_id, body.device_id,
            images=_seen(body), persona=voice.pack.persona,
        )
        return ChatResponse(reply=reply, conversation_id=conv_id)
    except BrainUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    owner: Owner = Depends(get_current_owner),
    cognition: Cognition = Depends(get_cognition),
    voice: VoiceBox = Depends(get_voice),
    db: Session = Depends(get_db),
):
    # Decoded BEFORE the stream opens: raising inside the generator would have
    # already sent 200 and an open event-stream, so the error could only arrive
    # as a chunk the HUD renders as if the assistant had said it.
    images = _seen(body)

    async def sse():
        try:
            async for event in cognition.respond_stream(
                db, owner.id, body.message, body.conversation_id, body.device_id,
                images=images, persona=voice.pack.persona,
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
