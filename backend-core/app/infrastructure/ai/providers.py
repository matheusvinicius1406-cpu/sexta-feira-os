"""
AI Providers - Abstract interfaces and implementations for multi-cloud AI
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import httpx

logger = logging.getLogger(__name__)


class AIProviderType(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    OLLAMA = "ollama"


@dataclass
class AIMessage:
    """AI message with role and content"""
    role: str  # "user" | "assistant" | "system"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    """AI response structure"""
    content: str
    model: str
    provider: str
    stop_reason: str = "stop"
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIRequest:
    """AI request structure"""
    messages: List[AIMessage]
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    tools: Optional[List[Dict[str, Any]]] = None
    system_prompt: Optional[str] = None
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAIProvider(ABC):
    """Abstract base for AI providers"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.provider_type: AIProviderType = None
    
    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate AI response"""
        pass
    
    @abstractmethod
    async def stream_generate(self, request: AIRequest) -> AsyncIterator[str]:
        """Stream AI response tokens"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider health"""
        pass


class OpenAIProvider(BaseAIProvider):
    """OpenAI provider (GPT-4, etc.)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        super().__init__(api_key, model)
        self.provider_type = AIProviderType.OPENAI
        self.base_url = "https://api.openai.com/v1"
    
    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate response via OpenAI API"""
        async with httpx.AsyncClient() as client:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            payload = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
            }
            
            if request.tools:
                payload["tools"] = request.tools
            
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            
            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                model=data["model"],
                provider=self.provider_type.value,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                stop_reason=data["choices"][0].get("finish_reason", "stop")
            )
    
    async def stream_generate(self, request: AIRequest) -> AsyncIterator[str]:
        """Stream response from OpenAI"""
        async with httpx.AsyncClient() as client:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            payload = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True,
            }
            
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=60.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
    
    async def health_check(self) -> bool:
        """Check OpenAI API health"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models/gpt-4-turbo",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False


class GeminiProvider(BaseAIProvider):
    """Google Gemini provider"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        super().__init__(api_key, model)
        self.provider_type = AIProviderType.GEMINI
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
    
    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate response via Gemini API"""
        async with httpx.AsyncClient() as client:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            payload = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
            }
            
            if request.tools:
                payload["tools"] = request.tools
            
            response = await client.post(
                f"{self.base_url}/chat/completions",
                params={"key": self.api_key},
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            
            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                model=data["model"],
                provider=self.provider_type.value,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                stop_reason=data["choices"][0].get("finish_reason", "stop")
            )
    
    async def stream_generate(self, request: AIRequest) -> AsyncIterator[str]:
        """Stream response from Gemini"""
        async with httpx.AsyncClient() as client:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            payload = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True,
            }
            
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                params={"key": self.api_key},
                json=payload,
                timeout=60.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
    
    async def health_check(self) -> bool:
        """Check Gemini API health"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    params={"key": self.api_key},
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False


class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        super().__init__(api_key, model)
        self.provider_type = AIProviderType.CLAUDE
        self.base_url = "https://api.anthropic.com/v1"
    
    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate response via Claude API"""
        async with httpx.AsyncClient() as client:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            payload = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
            
            if request.system_prompt:
                payload["system"] = request.system_prompt
            
            response = await client.post(
                f"{self.base_url}/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            
            return AIResponse(
                content=data["content"][0]["text"],
                model=data["model"],
                provider=self.provider_type.value,
                tokens_used=data.get("usage", {}).get("output_tokens", 0),
                stop_reason=data.get("stop_reason", "end_turn")
            )
    
    async def stream_generate(self, request: AIRequest) -> AsyncIterator[str]:
        """Stream response from Claude"""
        async with httpx.AsyncClient() as client:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            payload = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True,
            }
            
            if request.system_prompt:
                payload["system"] = request.system_prompt
            
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                json=payload,
                timeout=60.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            if data.get("delta", {}).get("type") == "text_delta":
                                yield data["delta"].get("text", "")
    
    async def health_check(self) -> bool:
        """Check Claude API health"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"x-api-key": self.api_key},
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Claude health check failed: {e}")
            return False


class OllamaProvider(BaseAIProvider):
    """Local Ollama provider (self-hosted)"""
    
    def __init__(self, endpoint: str, model: str = "llama2"):
        super().__init__("", model)
        self.provider_type = AIProviderType.OLLAMA
        self.endpoint = endpoint.rstrip("/")
    
    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate response via Ollama"""
        async with httpx.AsyncClient() as client:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            payload = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
                "stream": False,
            }
            
            response = await client.post(
                f"{self.endpoint}/api/chat",
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            
            return AIResponse(
                content=data["message"]["content"],
                model=data["model"],
                provider=self.provider_type.value,
                stop_reason="stop"
            )
    
    async def stream_generate(self, request: AIRequest) -> AsyncIterator[str]:
        """Stream response from Ollama"""
        async with httpx.AsyncClient() as client:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})
            
            payload = {
                "model": request.model or self.model,
                "messages": messages,
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
                "stream": True,
            }
            
            async with client.stream(
                "POST",
                f"{self.endpoint}/api/chat",
                json=payload,
                timeout=60.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
    
    async def health_check(self) -> bool:
        """Check Ollama health"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.endpoint}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
