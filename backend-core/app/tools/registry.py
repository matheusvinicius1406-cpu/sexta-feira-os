"""
Tool Registry - Central registry for tool definitions and metadata
Implements the registry pattern for managing available tools.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Tool categories for organization and filtering"""
    AUTOMATION = "automation"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    INFORMATION = "information"
    DEVICE_CONTROL = "device_control"
    INTEGRATION = "integration"
    CUSTOM = "custom"


@dataclass
class ToolParameter:
    """Tool parameter definition"""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for OpenAI schema"""
        result = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            result["enum"] = self.enum
        if self.default is not None:
            result["default"] = self.default
        return result


@dataclass
class ToolDefinition:
    """Complete tool definition with metadata"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: Optional[Callable] = None
    requires_confirmation: bool = False
    timeout_seconds: int = 30
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema"""
        required_params = [p.name for p in self.parameters if p.required]
        properties = {
            p.name: {
                "type": p.type,
                "description": p.description,
            }
            for p in self.parameters
        }
        
        # Add enum if present
        for param in self.parameters:
            if param.enum:
                properties[param.name]["enum"] = param.enum
            if param.default is not None:
                properties[param.name]["default"] = param.default
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_params,
                }
            }
        }


class ToolRegistry:
    """
    Central registry for tool definitions.
    Manages tool registration, lookup, and metadata.
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[ToolCategory, List[str]] = {
            category: [] for category in ToolCategory
        }
        logger.info("Tool Registry initialized")
    
    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool"""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, updating...")
        
        self._tools[tool.name] = tool
        self._categories[tool.category].append(tool.name)
        logger.info(f"✓ Registered tool: {tool.name} (category: {tool.category.value})")
    
    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name not in self._tools:
            logger.warning(f"Tool '{tool_name}' not found in registry")
            return False
        
        tool = self._tools.pop(tool_name)
        self._categories[tool.category].remove(tool_name)
        logger.info(f"Unregistered tool: {tool_name}")
        return True
    
    def get(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name"""
        return self._tools.get(tool_name)
    
    def get_all(self) -> List[ToolDefinition]:
        """Get all registered tools"""
        return list(self._tools.values())
    
    def get_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Get all tools in a category"""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names]
    
    def list_names(self, category: Optional[ToolCategory] = None) -> List[str]:
        """List tool names, optionally filtered by category"""
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())
    
    def exists(self, tool_name: str) -> bool:
        """Check if tool is registered"""
        return tool_name in self._tools
    
    def get_categories(self) -> List[ToolCategory]:
        """Get all available categories"""
        return list(ToolCategory)
    
    def clear(self) -> None:
        """Clear all registered tools (for testing)"""
        self._tools.clear()
        for category in self._categories:
            self._categories[category].clear()
        logger.info("Tool Registry cleared")


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance (lazy initialization)"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
