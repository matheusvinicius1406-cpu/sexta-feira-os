"""
AttachmentAnalyzer — Jarvis analisa PDFs, imagens e documentos.

Converts PDFs to images, extracts text, and feeds each kind to the brain in the
form it actually is: pixels as pixels, text as text. All local, all private.
"""
from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from app.brain.vision import VisionEngine, VisionUnavailable

if TYPE_CHECKING:
    from pypdf import PdfReader

logger = logging.getLogger("sexta-feira.attachments")

# Supported MIME types
SUPPORTED_TYPES = {
    # Images
    "image/jpeg": "image",
    "image/png": "image",
    "image/gif": "image",
    "image/webp": "image",
    "image/bmp": "image",
    # Documents
    "application/pdf": "pdf",
    "text/plain": "text",
    "text/markdown": "text",
    "text/csv": "text",
}


class AttachmentAnalyzer:
    """
    Analyzes file attachments with the local brain.

    - Images → direct analysis
    - PDFs → page-by-page rendering → vision analysis
    - Text → read and summarised as text, no image involved

    `brain` and `vision` normally speak to the SAME model; they are separate
    arguments because they are separate questions ("read this text" vs "look at
    this picture"), not separate models.
    """

    def __init__(self, vision: VisionEngine, brain=None):
        self.vision = vision
        self.brain = brain

    @staticmethod
    def detect_type(filename: str, content_type: str | None = None) -> str:
        """Detect attachment type from filename and MIME type."""
        if content_type and content_type in SUPPORTED_TYPES:
            return SUPPORTED_TYPES[content_type]

        # Fallback to extension
        ext = Path(filename).suffix.lower()
        ext_map = {
            ".jpg": "image", ".jpeg": "image", ".png": "image",
            ".gif": "image", ".webp": "image", ".bmp": "image",
            ".pdf": "pdf",
            ".txt": "text", ".md": "text", ".csv": "text",
        }
        return ext_map.get(ext, "unknown")

    async def analyze(
        self,
        file_data: bytes,
        filename: str,
        content_type: str | None = None,
        instruction: str | None = None,
    ) -> dict:
        """
        Analyze an attachment.

        Returns:
            {
                "type": "image" | "pdf" | "text" | "unknown",
                "filename": str,
                "analysis": str,
                "pages": int | None,  # for PDFs
            }
        """
        file_type = self.detect_type(filename, content_type)

        if file_type == "image":
            return await self._analyze_image(file_data, filename, instruction)
        elif file_type == "pdf":
            return await self._analyze_pdf(file_data, filename, instruction)
        elif file_type == "text":
            return await self._analyze_text(file_data, filename, instruction)
        else:
            return {
                "type": "unknown",
                "filename": filename,
                "analysis": f"Tipo de arquivo não suportado: {content_type or filename}",
                "pages": None,
            }

    async def _analyze_image(
        self, data: bytes, filename: str, instruction: str | None
    ) -> dict:
        """Analyze an image file."""
        prompt = instruction or (
            "Analise esta imagem em detalhes. Descreva o conteúdo, "
            "identifique texto visível, objetos, pessoas, e qualquer "
            "informação relevante. Em português."
        )
        analysis = await self.vision.analyze_image(data, prompt)
        return {
            "type": "image",
            "filename": filename,
            "analysis": analysis,
            "pages": None,
        }

    async def _analyze_pdf(
        self, data: bytes, filename: str, instruction: str | None
    ) -> dict:
        """Analyze a PDF by converting pages to images."""
        try:
            from pypdf import PdfReader
        except ImportError:
            return {
                "type": "pdf",
                "filename": filename,
                "analysis": (
                    "⚠️ pypdf não instalado. Execute: "
                    "pip install pypdf"
                ),
                "pages": None,
            }

        # Write PDF to temp file (pypdf needs a file path)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            reader = PdfReader(tmp_path)
            total_pages = len(reader.pages)
            max_pages = min(total_pages, 10)  # Limit to 10 pages

            page_analyses = []
            for i in range(max_pages):
                # Convert PDF page to image using pypdf + Pillow
                page_img = self._pdf_page_to_image(reader, i)
                if page_img:
                    prompt = (
                        f"Página {i + 1} de {total_pages} do documento '{filename}'. "
                        "Analise esta página: extraia texto, dados-chave, e resuma. "
                    )
                    if instruction:
                        prompt += f"\nInstrução adicional: {instruction}"
                    analysis = await self.vision.analyze_image(page_img, prompt)
                    page_analyses.append(f"--- Página {i + 1} ---\n{analysis}")

            if not page_analyses:
                return {
                    "type": "pdf",
                    "filename": filename,
                    "analysis": "Não foi possível extrair imagens do PDF. Tente com um arquivo diferente.",
                    "pages": total_pages,
                }

            # Combine all page analyses
            combined = f"📄 Documento: {filename} ({total_pages} páginas)\n\n"
            combined += "\n\n".join(page_analyses)

            if total_pages > max_pages:
                combined += f"\n\n⚠️ Analisadas {max_pages} de {total_pages} páginas (limite)."

            return {
                "type": "pdf",
                "filename": filename,
                "analysis": combined,
                "pages": total_pages,
            }
        finally:
            import os
            os.unlink(tmp_path)

    async def _analyze_text(
        self, data: bytes, filename: str, instruction: str | None
    ) -> dict:
        """Analyze a text file."""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("latin-1")
            except Exception:
                return {
                    "type": "text",
                    "filename": filename,
                    "analysis": "Não foi possível decodificar o arquivo de texto.",
                    "pages": None,
                }

        # Truncate very long texts
        max_chars = 8000
        truncated = len(text) > max_chars
        display_text = text[:max_chars] if truncated else text

        prompt = (
            f"Analise este arquivo de texto '{filename}':\n\n"
            f"{display_text}\n\n"
        )
        if truncated:
            prompt += f"(Texto truncado: {len(text)} caracteres no total)\n\n"
        if instruction:
            prompt += f"Instrução adicional: {instruction}\n\n"
        prompt += "Resuma, extraia pontos-chave, e forneça insights. Em português."

        # Text is asked as text. This used to call analyze_image with
        # `b"aGVsbG8="` — base64 for "hello", which is not an image at all — and
        # a comment conceding "actually, let's just use the brain's chat". It
        # never worked: _prepare_image hands those bytes to PIL, PIL refuses,
        # and every .txt/.md/.csv upload came back "Cannot decode image". The
        # fake pixel existed only because the text model and the vision model
        # were different processes; with one brain there is nothing to fake.
        if self.brain is None:
            raise VisionUnavailable(
                "Análise de texto precisa do cérebro local, que não foi fornecido."
            )
        analysis = await self.brain.chat([{"role": "user", "content": prompt}])

        return {
            "type": "text",
            "filename": filename,
            "analysis": text[:500] + "\n\n---\n\n" + analysis if len(text) > 200 else analysis,
            "pages": None,
        }

    @staticmethod
    def _pdf_page_to_image(reader: PdfReader, page_index: int) -> bytes | None:
        """
        Render a PDF page to JPEG image bytes.

        Uses pypdf to extract the page, then Pillow to render.
        Falls back to a simple text extraction if rendering fails.
        """
        try:
            page = reader.pages[page_index]
            # Try to extract text first
            text = page.extract_text()
            if text and len(text.strip()) > 20:
                # Create an image from the text
                from PIL import Image, ImageDraw

                # Wrap text into lines
                lines = []
                words = text.split()
                current_line = []
                for word in words:
                    current_line.append(word)
                    if len(" ".join(current_line)) > 80:
                        lines.append(" ".join(current_line))
                        current_line = []
                if current_line:
                    lines.append(" ".join(current_line))

                # Create image
                line_height = 16
                img_height = max(400, len(lines) * line_height + 40)
                img = Image.new("RGB", (800, img_height), "white")
                draw = ImageDraw.Draw(img)

                y = 20
                for line in lines[:50]:  # Max 50 lines
                    draw.text((20, y), line, fill="black")
                    y += line_height

                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                return buf.getvalue()
        except Exception as e:
            logger.debug("PDF page render failed: %s", e)

        return None
