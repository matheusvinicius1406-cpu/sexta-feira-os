"""
AI Orchestrator - Manages provider routing, fallback, and context injection
"""
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

from app.infrastructure.ai.providers import (
    BaseAIProvider, AIRequest, AIResponse, AIProviderType,
    OpenAIProvider, GeminiProvider, ClaudeProvider, OllamaProvider
)

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Provider routing strategies"""
    FALLBACK_CHAIN = "fallback_chain"  # Try primary, then fallback
    ROUND_ROBIN = "round_robin"  # Alternate providers
    COST_OPTIMIZED = "cost_optimized"  # Prefer cheaper providers
    LATENCY_OPTIMIZED = "latency_optimized"  # Prefer fastest
    CAPABILITY_MATCH = "capability_match"  # Match to task type


class PromptManager:
    """Manages prompt templates and engineering"""
    
    def __init__(self):
        self.system_prompts: Dict[str, str] = {
            "default": (
                "You are Jarvis, a personal AI assistant for Android. "
                "You are helpful, efficient, and always thinking ahead of the user's needs. "
                "Be concise but informative."
            ),
            "analysis": (
                "You are an expert analyst. Break down complex topics into clear, "
                "structured insights. Use data and examples."
            ),
            "planning": (
                "You are a strategic planner. Help users organize tasks, set priorities, "
                "and create actionable plans."
            ),
            "creative": (
                "You are a creative assistant. Generate innovative ideas, original content, "
                "and unique perspectives."
            ),
        }
    
    def get_prompt(self, prompt_type: str = "default") -> str:
        """Get system prompt by type"""
        return self.system_prompts.get(prompt_type, self.system_prompts["default"])
    
    def inject_context(self, prompt: str, context: Dict[str, Any]) -> str:
        """Inject runtime context into prompt"""
        result = prompt
        for key, value in context.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value))
        return result


class ContextInjector:
    """Injects memory, user context, and conversation history"""
    
    def __init__(self, memory_service=None):
        self.memory_service = memory_service
    
    async def enrich_request(
        self,
        request: AIRequest,
        user_id: str,
        conversation_id: Optional[str] = None,
        include_memory: bool = True
    ) -> AIRequest:
        """Enrich request with user context and memory"""
        # Add user context to metadata
        request.metadata["user_id"] = user_id
        request.metadata["conversation_id"] = conversation_id
        
        # Retrieve and inject relevant memories
        if include_memory and self.memory_service:
            try:
                # Get last few messages for context
                if len(request.messages) > 0:
                    last_message = request.messages[-1].content
                    memories = await self.memory_service.retrieve(user_id, last_message, limit=5)
                    
                    if memories:
                        context_text = "Relevant context from memory:\n"
                        for mem in memories:
                            context_text += f"- {mem.get('content', '')}\n"
                        
                        # Insert as system context
                        if request.system_prompt:
                            request.system_prompt += f"\n\n{context_text}"
                        else:
                            request.system_prompt = context_text
            except Exception as e:
                logger.warning(f"Failed to inject memory: {e}")
        
        return request


class ToolCallingEngine:
    """Handles function calling for available tools"""
    
    def __init__(self):
        self.tools: Dict[str, callable] = {}
    
    def register_tool(self, name: str, func: callable, schema: Dict[str, Any]):
        """Register a tool for function calling"""
        self.tools[name] = {"func": func, "schema": schema}
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tools schema"""
        return [
            {
                "type": "function",
                "function": tool["schema"]
            }
            for tool in self.tools.values()
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with given arguments"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        func = self.tools[tool_name]["func"]
        return await func(**arguments)


class ProviderFactory:
    """Factory for creating and managing AI provider instances"""
    
    @staticmethod
    def create_provider(
        provider_type: AIProviderType,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> BaseAIProvider:
        """Create provider instance"""
        if provider_type == AIProviderType.OPENAI:
            if not api_key:
                raise ValueError("OpenAI requires api_key")
            return OpenAIProvider(api_key, model or "gpt-4-turbo")
        
        elif provider_type == AIProviderType.GEMINI:
            if not api_key:
                raise ValueError("Gemini requires api_key")
            return GeminiProvider(api_key, model or "gemini-2.0-flash")
        
        elif provider_type == AIProviderType.CLAUDE:
            if not api_key:
                raise ValueError("Claude requires api_key")
            return ClaudeProvider(api_key, model or "claude-3-opus-20240229")
        
        elif provider_type == AIProviderType.OLLAMA:
            if not endpoint:
                raise ValueError("Ollama requires endpoint")
            return OllamaProvider(endpoint, model or "llama2")
        
        else:
            raise ValueError(f"Unknown provider: {provider_type}")


class AIOrchestrator:
    """Main orchestrator for multi-provider AI operations"""
    
    def __init__(
        self,
        default_provider: BaseAIProvider,
        fallback_providers: Optional[List[BaseAIProvider]] = None,
        routing_strategy: RoutingStrategy = RoutingStrategy.FALLBACK_CHAIN
    ):
        self.default_provider = default_provider
        self.fallback_providers = fallback_providers or []
        self.routing_strategy = routing_strategy
        self.prompt_manager = PromptManager()
        self.context_injector = ContextInjector()
        self.tool_engine = ToolCallingEngine()
    
    async def generate(
        self,
        request: AIRequest,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        prompt_type: str = "default"
    ) -> AIResponse:
        """Generate response with fallback chain"""
        # Enrich request with context
        if user_id:
            request = await self.context_injector.enrich_request(
                request, user_id, conversation_id
            )
        
        # Set system prompt if not provided
        if not request.system_prompt:
            request.system_prompt = self.prompt_manager.get_prompt(prompt_type)
        
        # Try providers in order
        providers = [self.default_provider] + self.fallback_providers
        last_error = None
        
        for provider in providers:
            try:
                logger.info(f"Attempting generation with {provider.provider_type.value}")
                response = await provider.generate(request)
                logger.info(f"Generation successful with {provider.provider_type.value}")
                return response
            except Exception as e:
                logger.warning(
                    f"Provider {provider.provider_type.value} failed: {e}. "
                    f"Trying fallback..."
                )
                last_error = e
                continue
        
        raise Exception(f"All providers failed. Last error: {last_error}")
    
    async def stream_generate(
        self,
        request: AIRequest,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        prompt_type: str = "default"
    ):
        """Stream generation with fallback"""
        # Enrich request with context
        if user_id:
            request = await self.context_injector.enrich_request(
                request, user_id, conversation_id
            )
        
        # Set system prompt if not provided
        if not request.system_prompt:
            request.system_prompt = self.prompt_manager.get_prompt(prompt_type)
        
        # Try providers in order
        providers = [self.default_provider] + self.fallback_providers
        last_error = None
        
        for provider in providers:
            try:
                logger.info(f"Attempting streaming with {provider.provider_type.value}")
                async for chunk in provider.stream_generate(request):
                    yield chunk
                return
            except Exception as e:
                logger.warning(
                    f"Provider {provider.provider_type.value} streaming failed: {e}. "
                    f"Trying fallback..."
                )
                last_error = e
                continue
        
        raise Exception(f"All providers failed. Last error: {last_error}")
