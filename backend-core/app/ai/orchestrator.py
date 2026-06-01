"""
AI Provider Abstraction and Orchestration with Jarvis Integration
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"


class AIProviderInterface(ABC):

    @abstractmethod
    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_provider_name(self) -> str:
        pass


class GeminiProviderAdapter(AIProviderInterface):

    def __init__(self):
        from app.jarvis import GeminiProvider, GeminiOrchestratorV2

        api_key = settings.gemini_api_key

        if not api_key:
            raise ValueError(
                "Gemini API key not configured. Check GEMINI_API_KEY in .env"
            )

        self.gemini_provider = GeminiProvider(api_key)
        self.orchestrator = GeminiOrchestratorV2(api_key)

        logger.info("Gemini provider initialized")

    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        try:
            response = await self.orchestrator.process_chat(
                message=message,
                user_context=context or {},
                temperature=0.7,
                max_tokens=2000,
            )

            if isinstance(response, str):
                response = {
                    "response": response,
                    "provider": "gemini",
                    "confidence": 0.95,
                    "metadata": {},
                }

            response.setdefault("provider", "gemini")
            response.setdefault("confidence", 0.95)
            response.setdefault("metadata", {})

            return response

        except Exception as e:
            logger.exception("Gemini error")

            return {
                "response": f"Gemini Error: {e}",
                "provider": "gemini",
                "confidence": 0.0,
                "metadata": {"error": str(e)},
            }

    async def get_provider_name(self) -> str:
        return "gemini"


class OpenAIProvider(AIProviderInterface):

    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        return {
            "response": f"[OpenAI Mock] {message}",
            "provider": "openai",
            "confidence": 0.5,
            "metadata": {},
        }

    async def get_provider_name(self) -> str:
        return "openai"


class ClaudeProvider(AIProviderInterface):

    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        return {
            "response": f"[Claude Mock] {message}",
            "provider": "claude",
            "confidence": 0.5,
            "metadata": {},
        }

    async def get_provider_name(self) -> str:
        return "claude"


class AIOrchestrator:

    def __init__(self):
        self.providers: Dict[str, AIProviderInterface] = {}
        self.default_provider = AIProvider.GEMINI.value
        self._init_providers()

    def _init_providers(self):

        try:
            self.providers[AIProvider.GEMINI.value] = GeminiProviderAdapter()
            logger.info("Gemini provider loaded")

        except Exception as e:
            logger.warning(f"Gemini provider not available: {e}")

        self.providers[AIProvider.OPENAI.value] = OpenAIProvider()
        self.providers[AIProvider.CLAUDE.value] = ClaudeProvider()

    async def process_chat(
        self,
        message: str,
        provider: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        try:
            selected = provider or self.default_provider

            if selected not in self.providers:
                selected = next(iter(self.providers.keys()))

            return await self.providers[selected].chat(
                message,
                context,
            )

        except Exception as e:
            logger.exception("Chat processing failed")

            return {
                "response": "Internal AI error.",
                "provider": provider or "unknown",
                "confidence": 0.0,
                "metadata": {"error": str(e)},
            }

    def get_available_providers(self):
        return list(self.providers.keys())


ai_orchestrator = AIOrchestrator()