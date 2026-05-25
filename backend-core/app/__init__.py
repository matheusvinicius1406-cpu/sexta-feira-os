"""App module - Sexta-Feira OS Backend Application"""

# Lazy imports to avoid circular dependencies with security module
# Import these modules in your code as needed:
# from app.tools import ToolRegistry, ToolResolver, ToolExecutor
# from app.services import ToolExecutionService, ConversationToolPipeline
# from app.android import IntentDispatcher, IntentService
# from app.api import tool_router

__all__ = [
    "ToolRegistry",
    "ToolResolver",
    "ToolExecutor",
    "ToolExecutionService",
    "ConversationToolPipeline",
    "IntentDispatcher",
    "IntentService",
    "tool_router",
]

def __getattr__(name):
    """Lazy loading of module attributes"""
    if name == "ToolRegistry":
        from app.tools import ToolRegistry
        return ToolRegistry
    elif name == "ToolResolver":
        from app.tools import ToolResolver
        return ToolResolver
    elif name == "ToolExecutor":
        from app.tools import ToolExecutor
        return ToolExecutor
    elif name == "ToolExecutionService":
        from app.services import ToolExecutionService
        return ToolExecutionService
    elif name == "ConversationToolPipeline":
        from app.services import ConversationToolPipeline
        return ConversationToolPipeline
    elif name == "IntentDispatcher":
        from app.android import IntentDispatcher
        return IntentDispatcher
    elif name == "IntentService":
        from app.android import IntentService
        return IntentService
    elif name == "tool_router":
        from app.api import tool_router
        return tool_router
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
