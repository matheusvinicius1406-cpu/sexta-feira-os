"""API module - REST endpoints and routers"""

# Lazy import to avoid circular dependencies
def __getattr__(name):
    if name == "tool_router":
        from app.api import tool_router
        return tool_router
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["tool_router"]
