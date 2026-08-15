"""
Vision — Jarvis enxerga, lê e analisa o mundo.

  GET  /api/v1/vision/status          vision engine health
  POST /api/v1/vision/analyze         analyze an image (upload or base64)
  POST /api/v1/vision/camera          analyze a camera frame
  POST /api/v1/vision/attachment      analyze any file attachment (PDF, image, text)
  POST /api/v1/vision/search          web search + content extraction
  POST /api/v1/vision/search_and_fetch search and fetch top result
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.auth.jwt import get_current_owner
from app.brain.attachments import AttachmentAnalyzer
from app.brain.vision import VisionEngine, VisionUnavailable
from app.brain.web_search import WebSearch
from app.browser.activity import record_search
from app.models.models import Owner

logger = logging.getLogger("sexta-feira.vision.router")

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])


# ── Request / Response models ──────────────────────────────

class ImageAnalysisRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image (JPEG/PNG)")
    prompt: str = Field(
        default="Descreva esta imagem em detalhes.",
        description="Question or instruction about the image",
    )


class CameraFrameRequest(BaseModel):
    frame_base64: str = Field(..., description="Base64-encoded camera frame (JPEG)")
    question: str | None = Field(
        default=None,
        description="Optional specific question about what the camera sees",
    )


class AttachmentAnalysisResponse(BaseModel):
    type: str
    filename: str
    analysis: str
    pages: int | None = None


class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)
    fetch_top: bool = Field(default=False, description="Also fetch full content of top result")


class WebSearchResponse(BaseModel):
    query: str
    results: list[dict]
    top_content: dict | None = None


# ── Dependency: VisionEngine singleton ─────────────────────

_vision_engine: VisionEngine | None = None
_web_search: WebSearch | None = None


def get_vision() -> VisionEngine:
    global _vision_engine
    if _vision_engine is None:
        _vision_engine = VisionEngine()
    return _vision_engine


def get_web_search() -> WebSearch:
    global _web_search
    if _web_search is None:
        _web_search = WebSearch()
    return _web_search


def _top_url(top_content) -> str | None:
    """The URL of the fetched result, when there is one — never invented."""
    if isinstance(top_content, dict):
        return top_content.get("url") or top_content.get("href") or None
    return None


# ── Endpoints ──────────────────────────────────────────────

@router.get("/status")
async def vision_status(
    owner: Owner = Depends(get_current_owner),
):
    """Check vision engine availability and which model is loaded."""
    vision = get_vision()
    health = await vision.check_health()
    return health


@router.post("/analyze")
async def analyze_image(
    body: ImageAnalysisRequest,
    owner: Owner = Depends(get_current_owner),
):
    """Analyze an image with a question/instruction."""
    vision = get_vision()
    try:
        result = await vision.analyze_image(body.image_base64, body.prompt)
        return {"analysis": result, "model": await vision._detect_vision_model()}
    except VisionUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.post("/camera")
async def analyze_camera_frame(
    body: CameraFrameRequest,
    owner: Owner = Depends(get_current_owner),
):
    """
    Analyze a live camera frame.

    Used by the Android app / web client to send periodic snapshots
    for environment awareness. Jarvis describes what it sees.
    """
    vision = get_vision()
    try:
        if body.question:
            result = await vision.answer_question(body.frame_base64, body.question)
        else:
            result = await vision.describe_scene(body.frame_base64)
        return {"analysis": result, "model": await vision._detect_vision_model()}
    except VisionUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.post("/attachment", response_model=AttachmentAnalysisResponse)
async def analyze_attachment(
    file: UploadFile = File(...),
    instruction: str | None = None,
    owner: Owner = Depends(get_current_owner),
):
    """
    Analyze any file attachment (PDF, image, text document).

    Jarvis will:
    - For images: describe and extract text (OCR)
    - For PDFs: render each page and analyze
    - For text: read, summarize, and extract insights
    """
    from app.core.di import get_kernel

    vision = get_vision()
    # The kernel's brain, not a new one: text attachments are read as text, and
    # reusing the live client keeps one connection pool and one warm model.
    analyzer = AttachmentAnalyzer(vision, brain=get_kernel().brain)

    file_data = await file.read()

    # Check file size limit
    size_mb = len(file_data) / (1024 * 1024)
    if size_mb > 10:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Arquivo muito grande: {size_mb:.1f}MB (máximo 10MB)",
        )

    try:
        result = await analyzer.analyze(
            file_data,
            file.filename or "unknown",
            file.content_type,
            instruction,
        )
        return result
    except VisionUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e


@router.post("/search", response_model=WebSearchResponse)
async def web_search(
    body: WebSearchRequest,
    owner: Owner = Depends(get_current_owner),
):
    """Search the web for information."""
    search = get_web_search()
    try:
        result = await search.search_and_fetch(
            body.query,
            max_results=body.max_results,
            fetch_top=body.fetch_top,
        )
        # The kernel's own "tab": every successful search is one open window.
        record_search(body.query, "search", len(result["results"]), _top_url(result["top_content"]))
        return result
    except Exception as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Busca web falhou: {e}",
        ) from e


@router.post("/search_and_fetch")
async def search_and_fetch(
    body: WebSearchRequest,
    owner: Owner = Depends(get_current_owner),
):
    """Search and fetch the full content of the top result."""
    search = get_web_search()
    result = await search.search_and_fetch(
        body.query,
        max_results=body.max_results,
        fetch_top=True,
    )
    record_search(body.query, "search_and_fetch", len(result["results"]), _top_url(result["top_content"]))
    return result
