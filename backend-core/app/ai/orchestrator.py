"""
AI Provider Abstraction and Orchestration with Jarvis Integration
Enhanced version using Gemini as primary provider with Jarvis system
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
import logging
import os

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"


class AIProviderInterface(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a chat message
        
        Returns:
            {
                "response": str,
                "provider": str,
                "confidence": float,
                "metadata": dict
            }
        """
        pass
    
    @abstractmethod
    async def get_provider_name(self) -> str:
        """Get provider name"""
        pass


class GeminiProviderAdapter(AIProviderInterface):
    """Gemini provider implementation with Jarvis integration"""
    
    def __init__(self):
        from app.jarvis import GeminiProvider, GeminiOrchestratorV2
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.gemini_provider = GeminiProvider(api_key)
        self.orchestrator = GeminiOrchestratorV2(api_key)
        logger.info("Gemini provider initialized")
    
    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send message to Gemini with context
        """
        try:
            # Use Jarvis orchestrator for enhanced processing
            response = await self.orchestrator.process_chat(
                message=message,
                user_context=context or {},
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Ensure response has required fields
            response["confidence"] = 0.95
            if "provider" not in response:
                response["provider"] = "gemini"
            
            return response
        except Exception as e:
            logger.error(f"Error in Gemini chat: {str(e)}")
            return {
                "response": f"Gemini Error: {str(e)}",
                "provider": "gemini",
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }
    
    async def get_provider_name(self) -> str:
        return "gemini"


class OpenAIProvider(AIProviderInterface):
    """OpenAI provider (fallback)"""
    
    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock OpenAI response"""
        return {
            "response": f"[OpenAI Mock] {message}",
            "provider": "openai",
            "confidence": 0.5,
            "metadata": {"model": "gpt-4", "mode": "mock"}
        }
    
    async def get_provider_name(self) -> str:
        return "openai"


class ClaudeProvider(AIProviderInterface):
    """Claude provider (fallback)"""
    
    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Mock Claude response"""
        return {
            "response": f"[Claude Mock] {message}",
            "provider": "claude",
            "confidence": 0.5,
            "metadata": {"model": "claude-2", "mode": "mock"}
        }
    
    async def get_provider_name(self) -> str:
        return "claude"


class AIOrchestrator:
    """Enhanced orchestrator with Jarvis system integration"""
    
    def __init__(self):
        self.providers: Dict[str, AIProviderInterface] = {}
        self._init_providers()
        self.default_provider = AIProvider.GEMINI.value
        logger.info(f"AI Orchestrator initialized. Default provider: {self.default_provider}")
    
    def _init_providers(self):
        """Initialize available providers"""
        # Try Gemini first (primary)
        try:
            self.providers[AIProvider.GEMINI.value] = GeminiProviderAdapter()
            logger.info("Gemini provider available")
        except Exception as e:
            logger.warning(f"Gemini provider not available: {e}")
        
        # Add fallback providers
        self.providers[AIProvider.OPENAI.value] = OpenAIProvider()
        self.providers[AIProvider.CLAUDE.value] = ClaudeProvider()
    
    async def process_chat(
        self,
        message: str,
        provider: str = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route message to appropriate AI provider
        """
        try:
            # Use default provider if not specified
            if not provider or provider not in self.providers:
                provider = self.default_provider
                if provider not in self.providers:
                    provider = list(self.providers.keys())[0]
                logger.info(f"Using provider: {provider}")
            
            selected_provider = self.providers[provider]
            response = await selected_provider.chat(message, context)
            return response
        except Exception as e:
            logger.error(f"Error processing chat: {str(e)}")
            return {
                "response": "I encountered an error processing your request.",
                "provider": provider or "unknown",
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }
    
    def get_available_providers(self) -> list:
        """Get list of available providers"""
        return list(self.providers.keys())


# Singleton instance
ai_orchestrator = AIOrchestrator()
