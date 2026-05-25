"""
Tool Execution Service - High-level service for tool execution workflows
Provides business logic for executing tools in context of conversations.
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from app.tools.executor import ToolExecutor, ExecutionResult
from app.tools.resolver import ToolResolver
from app.tools.registry import ToolDefinition, ToolCategory

logger = logging.getLogger(__name__)


class ToolExecutionService:
    """
    Service for executing tools with conversation context.
    Handles tool execution workflows, result formatting, and audit logging.
    """
    
    def __init__(self, executor: Optional[ToolExecutor] = None):
        self.executor = executor or ToolExecutor()
        logger.info("Tool Execution Service initialized")
    
    async def execute_tool_in_context(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a tool within conversation context.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            user_id: User executing the tool
            conversation_id: Optional conversation context
            context: Additional execution context
        
        Returns:
            Formatted result with metadata
        """
        logger.info(
            f"Executing tool '{tool_name}' for user {user_id} "
            f"in conversation {conversation_id}"
        )
        
        # Execute tool
        result = await self.executor.execute(
            tool_name=tool_name,
            parameters=parameters,
            user_id=user_id,
        )
        
        # Format result with metadata
        formatted = self._format_result(
            result,
            user_id=user_id,
            conversation_id=conversation_id,
            context=context,
        )
        
        return formatted
    
    async def execute_tool_chain(
        self,
        tools: List[Dict[str, Any]],
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a chain of tools sequentially.
        
        Args:
            tools: List of {tool_name, parameters} dicts
            user_id: User executing tools
            conversation_id: Conversation context
        
        Returns:
            List of execution results
        """
        results = []
        
        for i, tool_spec in enumerate(tools):
            tool_name = tool_spec.get("tool_name")
            parameters = tool_spec.get("parameters", {})
            
            logger.info(f"Executing tool {i+1}/{len(tools)}: {tool_name}")
            
            result = await self.execute_tool_in_context(
                tool_name=tool_name,
                parameters=parameters,
                user_id=user_id,
                conversation_id=conversation_id,
            )
            
            results.append(result)
            
            # Stop on failure if required
            if not result.get("success") and tool_spec.get("fail_on_error"):
                logger.warning(f"Tool chain stopped at step {i+1}")
                break
        
        return results
    
    def get_tool_availability(
        self,
        user_id: str,
        category: Optional[ToolCategory] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available tools for user.
        Can be extended for user-based tool restrictions.
        """
        tools = self.executor.list_tools(category=category)
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "requires_confirmation": tool.requires_confirmation,
            }
            for tool in tools
        ]
    
    def _format_result(
        self,
        result: ExecutionResult,
        user_id: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format execution result for API response"""
        return {
            "success": result.success,
            "tool_name": result.tool_name,
            "result": result.result,
            "error": result.error,
            "error_type": result.error_type,
            "execution_time_ms": result.execution_time_ms,
            "timestamp": result.timestamp.isoformat(),
            "user_id": user_id,
            "conversation_id": conversation_id,
        }
    
    def get_execution_summary(self, user_id: str) -> Dict[str, Any]:
        """Get execution summary for user"""
        stats = self.executor.get_statistics()
        
        return {
            "user_id": user_id,
            "statistics": stats,
            "recent_executions": [
                e.to_dict() for e in self.executor.get_execution_history(limit=10)
            ],
        }
