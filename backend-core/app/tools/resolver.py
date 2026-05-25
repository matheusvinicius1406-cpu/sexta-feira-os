"""
Tool Resolver - Resolves tool names to their definitions and handlers
Implements dependency resolution and tool discovery patterns.
"""
from typing import Optional, List, Dict, Any, Callable
import logging
from app.tools.registry import ToolRegistry, ToolDefinition, ToolCategory, get_registry

logger = logging.getLogger(__name__)


class ToolResolutionError(Exception):
    """Raised when tool resolution fails"""
    pass


class ToolResolver:
    """
    Resolves tool names to their definitions and execution handlers.
    Provides dependency injection and tool discovery.
    """
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or get_registry()
        self._handlers: Dict[str, Callable] = {}
        logger.info("Tool Resolver initialized")
    
    def register_handler(self, tool_name: str, handler: Callable) -> None:
        """Register execution handler for a tool"""
        if not self.registry.exists(tool_name):
            raise ToolResolutionError(f"Tool '{tool_name}' not registered in registry")
        
        self._handlers[tool_name] = handler
        logger.info(f"Registered handler for tool: {tool_name}")
    
    def resolve(self, tool_name: str) -> ToolDefinition:
        """
        Resolve a tool name to its definition.
        Raises ToolResolutionError if not found.
        """
        tool = self.registry.get(tool_name)
        if not tool:
            raise ToolResolutionError(f"Tool '{tool_name}' not found in registry")
        return tool
    
    def resolve_handler(self, tool_name: str) -> Callable:
        """
        Resolve a tool name to its execution handler.
        Raises ToolResolutionError if handler not registered.
        """
        if tool_name not in self._handlers:
            raise ToolResolutionError(f"Handler for tool '{tool_name}' not registered")
        return self._handlers[tool_name]
    
    def resolve_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Resolve all tools in a category"""
        return self.registry.get_by_category(category)
    
    def resolve_dependencies(self, tool_name: str) -> List[ToolDefinition]:
        """
        Resolve dependencies for a tool.
        Can be extended for tools with dependencies.
        """
        tool = self.resolve(tool_name)
        # Basic implementation: no dependencies yet
        # Can be extended to handle tool chains
        return [tool]
    
    def validate_parameters(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> bool:
        """
        Validate parameters against tool definition.
        Returns True if valid, raises exception otherwise.
        """
        tool = self.resolve(tool_name)
        required_params = {p.name for p in tool.parameters if p.required}
        provided_params = set(parameters.keys())
        
        # Check required parameters
        missing = required_params - provided_params
        if missing:
            raise ToolResolutionError(
                f"Missing required parameters for '{tool_name}': {missing}"
            )
        
        # Check parameter types (basic validation)
        for param in tool.parameters:
            if param.name in parameters:
                value = parameters[param.name]
                # Basic type check
                if not self._type_matches(value, param.type):
                    raise ToolResolutionError(
                        f"Parameter '{param.name}' has wrong type. "
                        f"Expected {param.type}, got {type(value).__name__}"
                    )
        
        return True
    
    @staticmethod
    def _type_matches(value: Any, type_name: str) -> bool:
        """Check if value matches expected type"""
        type_map = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_type = type_map.get(type_name)
        if expected_type is None:
            return True  # Unknown type, skip validation
        return isinstance(value, expected_type)
    
    def get_all_tools(self) -> List[ToolDefinition]:
        """Get all registered tools"""
        return self.registry.get_all()
    
    def has_handler(self, tool_name: str) -> bool:
        """Check if handler is registered for tool"""
        return tool_name in self._handlers
