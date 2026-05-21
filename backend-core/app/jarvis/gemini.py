"""
Gemini AI provider for Jarvis system
Unified interface to Google's Gemini API
"""

import logging
import json
from typing import Any, Dict, Optional, List, AsyncIterator
import asyncio

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Gemini AI Provider"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        if not genai:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
        
        self.api_key = api_key
        self.model_name = model
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        logger.info(f"Gemini provider initialized with model: {model}")
    
    async def chat(
        self,
        message: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: List[Dict[str, Any]] = None,
        context_history: List[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send chat message to Gemini
        
        Returns:
            {
                "response": str,
                "model": str,
                "provider": "gemini",
                "timestamp": str,
                "tokens_used": int,
                "finish_reason": str,
                "metadata": dict
            }
        """
        try:
            # Build message content
            contents = []
            
            # Add system prompt as first message
            if system_prompt:
                contents.append({
                    "role": "user",
                    "parts": [system_prompt]
                })
                contents.append({
                    "role": "model",
                    "parts": ["Understood. I will follow these instructions."]
                })
            
            # Add context history
            if context_history:
                for msg in context_history[-5:]:  # Last 5 messages
                    contents.append(msg)
            
            # Add current message
            contents.append({
                "role": "user",
                "parts": [message]
            })
            
            # Prepare generation config
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            
            # Generate response
            response = self.model.generate_content(
                contents,
                generation_config=genai.types.GenerationConfig(**generation_config),
                stream=False
            )
            
            # Handle potential errors
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                return {
                    "response": f"[Blocked: {response.prompt_feedback.block_reason}]",
                    "model": self.model_name,
                    "provider": "gemini",
                    "error": str(response.prompt_feedback.block_reason),
                    "finish_reason": "blocked"
                }
            
            # Extract response
            response_text = response.text if response.text else "[No response generated]"
            
            return {
                "response": response_text,
                "model": self.model_name,
                "provider": "gemini",
                "finish_reason": response.candidates[0].finish_reason.name if response.candidates else "unknown",
                "metadata": {
                    "usage": {
                        "prompt_tokens": 0,  # Gemini doesn't expose token count in free tier
                        "completion_tokens": 0,
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return {
                "response": f"Error: {str(e)}",
                "model": self.model_name,
                "provider": "gemini",
                "error": str(e),
                "finish_reason": "error"
            }
    
    async def stream_chat(
        self,
        message: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """
        Stream chat response from Gemini
        """
        try:
            # Build message content
            contents = []
            
            if system_prompt:
                contents.append({
                    "role": "user",
                    "parts": [system_prompt]
                })
                contents.append({
                    "role": "model",
                    "parts": ["Understood. I will follow these instructions."]
                })
            
            contents.append({
                "role": "user",
                "parts": [message]
            })
            
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            
            # Use streaming
            response = self.model.generate_content(
                contents,
                generation_config=genai.types.GenerationConfig(**generation_config),
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        
        except Exception as e:
            logger.error(f"Error streaming from Gemini: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def generate_with_context(
        self,
        message: str,
        user_memory: Dict[str, Any],
        agent_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        Generate response with user context and memory
        """
        # Build context-aware system prompt
        system_prompt = agent_prompt or "You are a helpful personal AI assistant."
        
        # Add memory context
        if user_memory:
            system_prompt += "\n\nContext about the user:\n"
            for key, value in user_memory.items():
                system_prompt += f"- {key}: {value}\n"
        
        # Call chat with context
        return await self.chat(
            message=message,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        return {
            "model": self.model_name,
            "provider": "gemini",
            "type": "generative",
            "capabilities": [
                "text_generation",
                "conversation",
                "analysis",
                "reasoning",
            ]
        }


class GeminiOrchestratorV2:
    """Enhanced Orchestrator using Gemini for all AI processing"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.provider = GeminiProvider(api_key, model)
        self.conversation_history: List[Dict[str, str]] = []
        logger.info("Gemini Orchestrator V2 initialized")
    
    async def process_chat(
        self,
        message: str,
        user_context: Dict[str, Any] = None,
        agent_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """Process chat message with full context"""
        
        # Generate response
        response = await self.provider.generate_with_context(
            message=message,
            user_memory=user_context or {},
            agent_prompt=agent_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Store in history
        self.conversation_history.append({
            "role": "user",
            "parts": [message]
        })
        self.conversation_history.append({
            "role": "model",
            "parts": [response["response"]]
        })
        
        # Keep history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return response
    
    async def analyze_text(
        self,
        text: str,
        analysis_type: str = "general",
    ) -> Dict[str, Any]:
        """Analyze text using Gemini"""
        
        prompts = {
            "sentiment": "Analyze the sentiment of this text. Respond with JSON: {sentiment: positive/negative/neutral, score: 0-1, reasoning: str}",
            "summary": "Summarize this text in 2-3 sentences",
            "keywords": "Extract 5 main keywords from this text",
            "general": "Analyze and provide insights about this text"
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        analysis_message = f"{prompt}\n\nText:\n{text}"
        
        return await self.provider.chat(analysis_message)
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return self.conversation_history.copy()
