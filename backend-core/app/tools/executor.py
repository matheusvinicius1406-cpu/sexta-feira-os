"""
Tool Executor - Executes tools with parameter validation and error handling
Implements the command pattern for tool execution.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging
import traceback

from app.tools.registry import ToolDefinition, ToolCategory
from app.tools.resolver import ToolResolver, ToolResolutionError

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of tool execution"""
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "error_type": self.error_type,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class ExecutionError(Exception):
    """Raised when tool execution fails"""
    pass


class ToolExecutor:
    """
    Executes registered tools with comprehensive error handling,
    timeout management, and execution tracking.
    """
    
    def __init__(self, resolver: Optional[ToolResolver] = None):
        self.resolver = resolver or ToolResolver()
        self._execution_history: List[ExecutionResult] = []
        self._max_history = 1000
        logger.info("Tool Executor initialized")
    
    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: Optional[str] = None,
        timeout_override: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Execute a tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            user_id: Optional user ID for audit logging
            timeout_override: Override tool's default timeout (seconds)
        
        Returns:
            ExecutionResult with success/failure details
        """
        start_time = datetime.utcnow()
        
        try:
            # Resolve tool definition
            tool = self.resolver.resolve(tool_name)
            
            # Validate parameters
            self.resolver.validate_parameters(tool_name, parameters)
            
            # Get handler
            handler = self.resolver.resolve_handler(tool_name)
            
            # Execute with timeout
            timeout = timeout_override or tool.timeout_seconds
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**parameters),
                    timeout=timeout
                )
            else:
                # Run sync function in thread pool to prevent blocking
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, handler, **parameters),
                    timeout=timeout
                )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            execution_result = ExecutionResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time_ms=execution_time,
            )
            
            logger.info(
                f"✓ Tool executed: {tool_name} (user: {user_id}, "
                f"time: {execution_time:.2f}ms)"
            )
            
            self._record_execution(execution_result)
            return execution_result
            
        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            tool = self.resolver.registry.get(tool_name)
            error_msg = f"Tool execution timeout ({tool.timeout_seconds}s)"
            
            execution_result = ExecutionResult(
                tool_name=tool_name,
                success=False,
                error=error_msg,
                error_type="TimeoutError",
                execution_time_ms=execution_time,
            )
            
            logger.warning(f"⚠ Timeout executing '{tool_name}': {error_msg}")
            self._record_execution(execution_result)
            return execution_result
            
        except ToolResolutionError as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            execution_result = ExecutionResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                error_type="ResolutionError",
                execution_time_ms=execution_time,
            )
            
            logger.error(f"✗ Resolution error for '{tool_name}': {e}")
            self._record_execution(execution_result)
            return execution_result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            error_details = traceback.format_exc()
            
            execution_result = ExecutionResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                execution_time_ms=execution_time,
            )
            
            logger.error(
                f"✗ Error executing '{tool_name}': {e}\n{error_details}"
            )
            self._record_execution(execution_result)
            return execution_result
    
    def list_tools(
        self,
        category: Optional[ToolCategory] = None
    ) -> List[ToolDefinition]:
        """List available tools"""
        if category:
            return self.resolver.resolve_by_category(category)
        return self.resolver.get_all_tools()
    
    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool definition"""
        try:
            return self.resolver.resolve(tool_name)
        except ToolResolutionError:
            return None
    
    def get_execution_history(
        self,
        tool_name: Optional[str] = None,
        limit: int = 50
    ) -> List[ExecutionResult]:
        """Get execution history"""
        history = self._execution_history
        if tool_name:
            history = [e for e in history if e.tool_name == tool_name]
        return history[-limit:]
    
    def _record_execution(self, result: ExecutionResult) -> None:
        """Record execution in history"""
        self._execution_history.append(result)
        
        # Trim history if it exceeds max size
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]
    
    def clear_history(self) -> None:
        """Clear execution history"""
        self._execution_history.clear()
        logger.info("Execution history cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self._execution_history:
            return {"total": 0}
        
        total = len(self._execution_history)
        successful = sum(1 for e in self._execution_history if e.success)
        failed = total - successful
        
        avg_time = sum(e.execution_time_ms for e in self._execution_history) / total
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "average_execution_time_ms": avg_time,
        }
