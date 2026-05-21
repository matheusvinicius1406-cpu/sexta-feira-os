"""
Tools & Automation Router - API for tool execution
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
import logging

from app.core.security import get_current_user
from app.core.di import get_container
from app.application.dtos.responses import AutomationTaskRequest, AutomationTaskResponse
from app.infrastructure.ai.tools import ToolCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/tools", tags=["tools"])


@router.get("/list")
async def list_tools(
    category: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """List available tools"""
    try:
        container = get_container()
        if not container.tool_executor:
            raise HTTPException(status_code=503, detail="Tool executor not initialized")
        
        # Parse category if provided
        tool_category = None
        if category:
            try:
                tool_category = ToolCategory(category)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        
        tools = container.tool_executor.list_tools(tool_category)
        
        return {
            "success": True,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category.value,
                    "parameters": [p.to_dict() for p in tool.parameters],
                    "requires_confirmation": tool.requires_confirmation,
                    "timeout": tool.timeout_seconds,
                }
                for tool in tools
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/{tool_name}")
async def get_tool_schema(
    tool_name: str,
    current_user = Depends(get_current_user)
):
    """Get tool schema for OpenAI function calling"""
    try:
        container = get_container()
        if not container.tool_executor:
            raise HTTPException(status_code=503, detail="Tool executor not initialized")
        
        definition = container.tool_executor.get_tool_definition(tool_name)
        if not definition:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
        
        return {
            "success": True,
            "schema": definition.to_openai_schema()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute/{tool_name}")
async def execute_tool(
    tool_name: str,
    args: dict,
    current_user = Depends(get_current_user)
):
    """Execute a tool"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        container = get_container()
        if not container.tool_executor:
            raise HTTPException(status_code=503, detail="Tool executor not initialized")
        
        # Execute tool
        result = await container.tool_executor.execute(tool_name, args, user_id)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return {
            "success": True,
            "tool": tool_name,
            "result": result.data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def list_categories(
    current_user = Depends(get_current_user)
):
    """List available tool categories"""
    return {
        "success": True,
        "categories": [c.value for c in ToolCategory]
    }


@router.post("/automation/create")
async def create_automation_task(
    request: AutomationTaskRequest,
    current_user = Depends(get_current_user)
):
    """Create an automation task"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        # TODO: Implement automation task creation
        # For now, return placeholder
        return {
            "success": True,
            "task_id": f"task_{user_id}_{request.name}",
            "task": {
                "id": f"task_{user_id}_{request.name}",
                "name": request.name,
                "task_type": request.task_type,
                "enabled": request.enabled,
                "created_at": "2024-01-01T00:00:00Z",
            }
        }
    except Exception as e:
        logger.error(f"Error creating automation task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/list")
async def list_automation_tasks(
    current_user = Depends(get_current_user)
):
    """List user's automation tasks"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        # TODO: Implement task listing from database
        # For now, return empty list
        return {
            "success": True,
            "tasks": []
        }
    except Exception as e:
        logger.error(f"Error listing automation tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
