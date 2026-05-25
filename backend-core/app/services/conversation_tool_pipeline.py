"""
Conversation Tool Pipeline - Integrates tools into conversation flow
Provides tool-aware conversation processing for AI orchestration.
"""
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ConversationToolPipeline:
    """
    Manages tool execution within conversation context.
    Integrates tool calls from AI responses into the conversation flow.
    """
    
    def __init__(self, tool_execution_service=None):
        """
        Initialize conversation tool pipeline.
        
        Args:
            tool_execution_service: Service for tool execution
        """
        self.tool_execution_service = tool_execution_service
        logger.info("Conversation Tool Pipeline initialized")
    
    async def process_response_with_tools(
        self,
        ai_response: Dict[str, Any],
        user_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        """
        Process AI response that may contain tool calls.
        
        Args:
            ai_response: Response from AI provider
            user_id: User ID
            conversation_id: Conversation ID
        
        Returns:
            Processed response with tool execution results
        """
        # Check if response contains tool calls
        tool_calls = self._extract_tool_calls(ai_response)
        
        if not tool_calls:
            return ai_response
        
        # Execute tools
        tool_results = []
        for tool_call in tool_calls:
            result = await self._execute_tool_call(
                tool_call,
                user_id,
                conversation_id,
            )
            tool_results.append(result)
        
        # Merge results back into response
        enriched_response = self._merge_tool_results(ai_response, tool_results)
        
        return enriched_response
    
    def _extract_tool_calls(self, ai_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tool calls from AI response"""
        # Handle different AI provider response formats
        
        # OpenAI format
        if "tool_calls" in ai_response:
            return ai_response["tool_calls"]
        
        # Alternative format
        if "function_calls" in ai_response:
            return ai_response["function_calls"]
        
        return []
    
    async def _execute_tool_call(
        self,
        tool_call: Dict[str, Any],
        user_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        """Execute a single tool call"""
        if not self.tool_execution_service:
            return {
                "tool_name": tool_call.get("name"),
                "success": False,
                "error": "Tool execution service not configured",
            }
        
        tool_name = tool_call.get("name")
        parameters = tool_call.get("arguments", {})
        
        result = await self.tool_execution_service.execute_tool_in_context(
            tool_name=tool_name,
            parameters=parameters,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        
        return result
    
    def _merge_tool_results(
        self,
        ai_response: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Merge tool execution results into AI response"""
        enriched = ai_response.copy()
        enriched["tool_execution_results"] = tool_results
        
        # Add execution summary
        successful = sum(1 for r in tool_results if r.get("success"))
        enriched["tools_executed"] = {
            "total": len(tool_results),
            "successful": successful,
            "failed": len(tool_results) - successful,
        }
        
        return enriched
    
    async def process_conversation_with_tools(
        self,
        user_message: str,
        conversation_context: Dict[str, Any],
        ai_provider,
    ) -> Dict[str, Any]:
        """
        Process conversation turn with tool capability.
        
        Args:
            user_message: User's message
            conversation_context: Conversation state
            ai_provider: AI provider instance
        
        Returns:
            Processed response with tool results
        """
        # Get AI response
        ai_response = await ai_provider.process_message(
            user_message,
            conversation_context,
        )
        
        # Process tool calls if any
        user_id = conversation_context.get("user_id")
        conversation_id = conversation_context.get("conversation_id")
        
        if user_id and conversation_id:
            processed = await self.process_response_with_tools(
                ai_response,
                user_id,
                conversation_id,
            )
            return processed
        
        return ai_response
