"""
Vision — Jarvis的眼睛, enxergar e analisar o mundo ao redor.

Uses Ollama vision models (llava, llama3.2-vision) for:
  * Camera frame analysis (what's in front of the user?)
  * Image understanding (photos, screenshots, diagrams)
  * Document analysis (OCR, layout understanding)
  * Scene description (environment awareness)

All processing is LOCAL — no image ever leaves the machine.
"""
from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

import httpx
from PIL import Image

from app.core.config import settings

logger = logging.getLogger("sexta-feira.vision")

# Supported vision models in priority order
VISION_MODELS = [
    "llava:7b",
    "llava:13b",
    "bakllava",
    "moondream",
]

# Image processing limits
MAX_IMAGE_SIZE_MB = 10
MAX_DIMENSION = 1024  # Resize larger images to this max dimension
JPEG_QUALITY = 85


class VisionUnavailable(RuntimeError):
    """Raised when no vision model is available in Ollama."""


class VisionEngine:
    """
    Local vision analysis engine powered by Ollama vision models.
    
    Supports:
    - Single image analysis (describe, OCR, Q&A)
    - Batch image analysis
    - Camera frame streaming analysis
    - Document page analysis
    """

    def __init__(self, endpoint: str | None = None, model: str | None = None):
        self.endpoint = (endpoint or settings.ollama_endpoint).rstrip("/")
        self._model_preference = model or settings.vision_model or None
        self._client = httpx.AsyncClient(
            base_url=self.endpoint, timeout=httpx.Timeout(180.0)
        )
        self._available_model: str | None = None
        self._max_dim = settings.vision_max_image_dim
        self._jpeg_quality = settings.vision_jpeg_quality

    async def aclose(self) -> None:
        await self._client.aclose()

    # ── Model discovery ──────────────────────────────────────

    async def _detect_vision_model(self) -> str:
        """Find the best available vision model in Ollama."""
        if self._available_model is not None:
            return self._available_model

        if self._model_preference:
            try:
                r = await self._client.get("/api/tags", timeout=5.0)
                r.raise_for_status()
                models = [m["name"] for m in r.json().get("models", [])]
                # Check if preferred model is available
                for m in models:
                    if self._model_preference in m:
                        self._available_model = m
                        logger.info("Using preferred vision model: %s", m)
                        return m
            except Exception:
                pass

        # Auto-detect best available
        try:
            r = await self._client.get("/api/tags", timeout=5.0)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            for preferred in VISION_MODELS:
                for m in models:
                    if preferred in m:
                        self._available_model = m
                        logger.info("Auto-detected vision model: %s", m)
                        return m
        except Exception as e:
            logger.warning("Failed to list Ollama models: %s", e)

        raise VisionUnavailable(
            "Nenhum modelo de visão encontrado no Ollama. "
            "Rode: ollama pull llava:7b"
        )

    async def check_health(self) -> dict:
        """Check vision engine availability."""
        try:
            model = await self._detect_vision_model()
            return {"available": True, "model": model, "endpoint": self.endpoint}
        except VisionUnavailable as e:
            return {"available": False, "error": str(e), "endpoint": self.endpoint}

    # ── Image preprocessing ──────────────────────────────────

    @staticmethod
    def _prepare_image(
        image_data: bytes | str,
        max_dim: int = MAX_DIMENSION,
        quality: int = JPEG_QUALITY,
    ) -> str:
        """
        Normalize image to JPEG bytes and return as base64 string.
        
        Accepts raw bytes (JPEG/PNG) or base64-encoded string.
        Resizes oversized images to save VRAM and speed up inference.
        """
        # Decode base64 if needed
        if isinstance(image_data, str):
            # Strip data URL prefix if present
            if "," in image_data and image_data.startswith("data:"):
                image_data = image_data.split(",", 1)[1]
            raw = base64.b64decode(image_data)
        else:
            raw = image_data

        try:
            img = Image.open(io.BytesIO(raw))
        except Exception as e:
            raise ValueError(f"Cannot decode image: {e}") from e

        # Convert to RGB if needed (RGBA, palette, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Resize if too large
        w, h = img.size
        if max(w, h) > max_dim:
            ratio = max_dim / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            logger.debug("Resized image %dx%d -> %dx%d", w, h, *new_size)

        # Encode to JPEG
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    def _image_from_bytes(data: bytes) -> Image.Image:
        """Open a PIL Image from raw bytes."""
        return Image.open(io.BytesIO(data))

    # ── Core analysis ────────────────────────────────────────

    async def analyze_image(
        self,
        image_data: bytes | str,
        prompt: str = "Descreva esta imagem em detalhes, em português.",
        model: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """
        Analyze a single image with a vision model.
        
        Args:
            image_data: Raw bytes (JPEG/PNG) or base64-encoded string
            prompt: Question/instruction about the image
            model: Override model (auto-detect if None)
            temperature: Lower = more deterministic
            
        Returns:
            Text description/analysis from the vision model
        """
        vision_model = model or await self._detect_vision_model()
        b64_image = self._prepare_image(image_data, max_dim=self._max_dim, quality=self._jpeg_quality)

        payload = {
            "model": vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64_image],
                }
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 1024,
            },
        }

        try:
            r = await self._client.post("/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except httpx.ConnectError as e:
            raise VisionUnavailable(
                f"Ollama não respondeu em {self.endpoint}. Rode `ollama serve`."
            ) from e

    async def analyze_images_batch(
        self,
        images: list[bytes | str],
        prompt: str = "Analise todas estas imagens e descreva o que enxerga, em português.",
        model: str | None = None,
    ) -> str:
        """
        Analyze multiple images in a single request.
        
        Useful for comparing images or analyzing a sequence of camera frames.
        """
        vision_model = model or await self._detect_vision_model()
        b64_images = [self._prepare_image(img) for img in images]

        payload = {
            "model": vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": b64_images,
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048,
            },
        }

        try:
            r = await self._client.post("/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except httpx.ConnectError as e:
            raise VisionUnavailable(
                f"Ollama não respondeu em {self.endpoint}. Rode `ollama serve`."
            ) from e

    # ── Specialized analysis ─────────────────────────────────

    async def describe_scene(self, image_data: bytes | str) -> str:
        """Describe what's in the scene (camera analysis)."""
        prompt = (
            "Você é Sexta-Feira, o assistente pessoal do seu dono. "
            "Analise esta imagem de câmera e descreva: "
            "1) O que está vendo no ambiente; "
            "2) Se há pessoas (sem identificar rostos por nome, apenas contagem); "
            "3) Objetos importantes ou notáveis; "
            "4) Texto visível (se houver); "
            "5) Qualquer coisa que pareça fora do comum. "
            "Seja conciso mas informativo. Em português."
        )
        return await self.analyze_image(image_data, prompt, temperature=0.2)

    async def read_text(self, image_data: bytes | str) -> str:
        """OCR — extract all visible text from an image."""
        prompt = (
            "Extraia TODO o texto visível nesta imagem. "
            "Mantenha a formatação original (parágrafos, listas, tabelas). "
            "Se não houver texto, responda 'Nenhum texto detectado'. "
            "Em português."
        )
        return await self.analyze_image(image_data, prompt, temperature=0.1)

    async def analyze_document_page(
        self, image_data: bytes | str, instruction: str | None = None
    ) -> str:
        """Analyze a single document page (PDF rendered as image)."""
        prompt = (
            "Esta é uma página de documento. Analise-a e: "
            "1) Identifique o tipo de documento (contrato, nota fiscal, receipt, etc.); "
            "2) Extraia os dados principais; "
            "3) Resuma o conteúdo; "
        )
        if instruction:
            prompt += f"\nInstrução adicional: {instruction}"
        return await self.analyze_image(image_data, prompt, temperature=0.2)

    async def answer_question(
        self, image_data: bytes | str, question: str
    ) -> str:
        """Answer a specific question about an image."""
        return await self.analyze_image(
            image_data,
            f"Responda esta pergunta sobre a imagem: {question}",
            temperature=0.3,
        )
