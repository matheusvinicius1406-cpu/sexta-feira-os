"""
Tool Router - FastAPI router for tool execution API
Provides REST endpoints for tool discovery and execution.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging

from app.core.security import get_current_user
from app.core.di import get_container
from app.schemas.tool_schemas import (
    ToolListResponse,
    ToolExecutionRequest,
    ToolExecutionResponse,
    ToolChainRequest,
    ToolChainResponse,
    ToolStatisticsResponse,
    ToolParameterSchema,
    ToolDefinitionSchema,
)
from app.tools.registry import ToolCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/tools", tags=["tools"])


@router.get("/list", response_model=ToolListResponse)
async def list_tools(
    category: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """List available tools with optional category filter"""
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
        
        tool_schemas = [
            ToolDefinitionSchema(
                name=tool.name,
                description=tool.description,
                category=tool.category.value,
                parameters=[
                    ToolParameterSchema(
                        name=p.name,
                        type=p.type,
                        description=p.description,
                        required=p.required,
                        default=p.default,
                        enum=p.enum,
                    )
                    for p in tool.parameters
                ],
                requires_confirmation=tool.requires_confirmation,
                timeout_seconds=tool.timeout_seconds,
                tags=tool.tags,
                version=tool.version,
            )
            for tool in tools
        ]
        
        return ToolListResponse(success=True, tools=tool_schemas)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_categories(
    current_user = Depends(get_current_user)
):
    """Get available tool categories"""
    try:
        container = get_container()
        if not container.tool_executor:
            raise HTTPException(status_code=503, detail="Tool executor not initialized")
        
        categories = [cat.value for cat in ToolCategory]
        
        return {
            "success": True,
            "categories": categories,
            "count": len(categories)
        }
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/{tool_name}")
async def get_tool_schema(
    tool_name: str,
    current_user = Depends(get_current_user)
):
    """Get detailed schema for a specific tool"""
    try:
        container = get_container()
        if not container.tool_executor:
            raise HTTPException(status_code=503, detail="Tool executor not initialized")
        
        definition = container.tool_executor.get_tool_definition(tool_name)
        if not definition:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
        
        schema = ToolDefinitionSchema(
            name=definition.name,
            description=definition.description,
            category=definition.category.value,
            parameters=[
                ToolParameterSchema(
                    name=p.name,
                    type=p.type,
                    description=p.description,
                    required=p.required,
                    default=p.default,
                    enum=p.enum,
                )
                for p in definition.parameters
            ],
            requires_confirmation=definition.requires_confirmation,
            timeout_seconds=definition.timeout_seconds,
            tags=definition.tags,
            version=definition.version,
        )
        
        return {
            "success": True,
            "schema": schema,
            "openai_schema": definition.to_openai_schema()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    request: ToolExecutionRequest,
    current_user = Depends(get_current_user)
):
    """Execute a tool with provided parameters"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        container = get_container()
        if not container.tool_executor:
            raise HTTPException(status_code=503, detail="Tool executor not initialized")
        
        # Execute tool
        result = await container.tool_executor.execute(
            tool_name=request.tool_name,
            parameters=request.parameters,
            user_id=user_id,
            timeout_override=request.timeout_override,
        )
        
        return ToolExecutionResponse(
            success=result.success,
            tool_name=result.tool_name,
            result=result.result,
            error=result.error,
            error_type=result.error_type,
            execution_time_ms=result.execution_time_ms,
            timestamp=result.timestamp.isoformat(),
            user_id=user_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-chain", response_model=ToolChainResponse)
async def execute_tool_chain(
    request: ToolChainRequest,
    current_user = Depends(get_current_user)
):
    """Execute multiple tools in sequence"""
    try:
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        
        container = get_container()
        if not container.tool_execution_service:
            raise HTTPException(status_code=503, detail="Tool execution service not initialized")
        
        # Execute tool chain
        results = await container.tool_execution_service.execute_tool_chain(
            tools=request.tools,
            user_id=user_id,
        )
        
        # Convert results
        execution_results = [
            ToolExecutionResult(
                tool_name=r.get("tool_name"),
                success=r.get("success", False),
                result=r.get("result"),
                error=r.get("error"),
                error_type=r.get("error_type"),
                execution_time_ms=r.get("execution_time_ms", 0),
                timestamp=r.get("timestamp", ""),
            )
            for r in results
        ]
        
        total_time = sum(r.execution_time_ms for r in execution_results)
        successful = sum(1 for r in execution_results if r.success)
        
        return ToolChainResponse(
            success=all(r.success for r in execution_results),
            tools_executed={
                "total": len(execution_results),
                "successful": successful,
                "failed": len(execution_results) - successful,
            },
            results=execution_results,
            total_execution_time_ms=total_time,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing tool chain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=ToolStatisticsResponse)
async def get_statistics(
    tool_name: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get tool execution statistics"""
    try:
        container = get_container()
        if not container.tool_executor:
            raise HTTPException(status_code=503, detail="Tool executor not initialized")
        
        stats = container.tool_executor.get_statistics()
        
        return ToolStatisticsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
