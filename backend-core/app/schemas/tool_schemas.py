"""
Tool Schemas - Pydantic models for tool-related API requests and responses
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum


class ToolCategory(str, Enum):
    """Tool categories"""
    AUTOMATION = "automation"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    INFORMATION = "information"
    DEVICE_CONTROL = "device_control"
    INTEGRATION = "integration"
    CUSTOM = "custom"


class ToolParameterSchema(BaseModel):
    """Tool parameter schema"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class ToolDefinitionSchema(BaseModel):
    """Tool definition schema"""
    name: str
    description: str
    category: str
    parameters: List[ToolParameterSchema] = []
    requires_confirmation: bool = False
    timeout_seconds: int = 30
    tags: List[str] = []
    version: str = "1.0.0"


class ToolExecutionRequest(BaseModel):
    """Tool execution request"""
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    requires_confirmation: bool = Field(default=False, description="Whether to wait for confirmation")
    timeout_override: Optional[float] = Field(default=None, description="Override tool timeout (seconds)")


class ToolExecutionResult(BaseModel):
    """Tool execution result"""
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: float
    timestamp: str


class ToolListResponse(BaseModel):
    """Response for listing tools"""
    success: bool
    tools: List[ToolDefinitionSchema]
    count: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        self.count = len(self.tools)


class ToolExecutionResponse(BaseModel):
    """Response for tool execution"""
    success: bool
    tool_name: str
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: float
    timestamp: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ToolChainRequest(BaseModel):
    """Request to execute a chain of tools"""
    tools: List[Dict[str, Any]] = Field(
        ...,
        description="List of {tool_name, parameters, fail_on_error} dicts"
    )


class ToolChainResponse(BaseModel):
    """Response for tool chain execution"""
    success: bool
    tools_executed: Dict[str, int] = Field(default_factory=dict)
    results: List[ToolExecutionResult] = []
    total_execution_time_ms: float = 0.0


class ToolStatisticsResponse(BaseModel):
    """Tool execution statistics"""
    total: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0.0
    average_execution_time_ms: float = 0.0
