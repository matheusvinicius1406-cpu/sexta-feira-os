"""
Tool Execution Engine - Register and execute tools/functions
"""
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import inspect

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Tool categories"""
    SYSTEM = "system"
    BROWSER = "browser"
    AUTOMATION = "automation"
    ANDROID = "android"
    CALENDAR = "calendar"
    MESSAGING = "messaging"
    SEARCH = "search"
    KNOWLEDGE = "knowledge"


@dataclass
class ToolParameter:
    """Parameter definition for a tool"""
    name: str
    description: str
    param_type: str  # "string", "integer", "boolean", "array", "object"
    required: bool = True
    default: Optional[Any] = None
    enum_values: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        obj = {
            "name": self.name,
            "description": self.description,
            "type": self.param_type,
        }
        if self.enum_values:
            obj["enum"] = self.enum_values
        if self.min_value is not None:
            obj["minimum"] = self.min_value
        if self.max_value is not None:
            obj["maximum"] = self.max_value
        return obj


@dataclass
class ToolDefinition:
    """Tool definition"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter] = field(default_factory=list)
    requires_permission: Optional[str] = None
    requires_confirmation: bool = False
    timeout_seconds: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.param_type,
                "description": param.description,
            }
            if param.enum_values:
                properties[param.name]["enum"] = param.enum_values
            if param.min_value is not None:
                properties[param.name]["minimum"] = param.min_value
            if param.max_value is not None:
                properties[param.name]["maximum"] = param.max_value
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }


class ToolResult:
    """Result from tool execution"""
    
    def __init__(self, success: bool, data: Any, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }
    
    def to_string(self) -> str:
        """Convert to string for LLM"""
        if self.success:
            return json.dumps(self.data)
        else:
            return f"Error: {self.error}"


class ToolExecutor:
    """Executes registered tools"""
    
    def __init__(self):
        self.tools: Dict[str, tuple[Callable, ToolDefinition]] = {}
    
    def register_tool(
        self,
        func: Callable,
        definition: ToolDefinition
    ) -> None:
        """Register a tool"""
        self.tools[definition.name] = (func, definition)
        logger.info(f"Registered tool: {definition.name} ({definition.category})")
    
    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool definition"""
        if tool_name in self.tools:
            return self.tools[tool_name][1]
        return None
    
    def get_tools_for_openai(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI format"""
        return [
            {
                "type": "function",
                "function": definition.to_openai_schema()
            }
            for _, definition in self.tools.values()
        ]
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> ToolResult:
        """Execute a tool"""
        if tool_name not in self.tools:
            return ToolResult(False, None, f"Unknown tool: {tool_name}")
        
        func, definition = self.tools[tool_name]
        
        try:
            # Check if function is async
            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            
            return ToolResult(True, result)
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}: {e}")
            return ToolResult(False, None, str(e))
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolDefinition]:
        """List available tools"""
        tools = [definition for _, definition in self.tools.values()]
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        return tools


class DefaultTools:
    """Default tools registry"""
    
    @staticmethod
    async def web_search(query: str, limit: int = 5) -> Dict[str, Any]:
        """Search the web"""
        # Placeholder: integrate with search API
        return {
            "query": query,
            "results": [
                {"title": f"Result {i+1}", "url": f"https://example.com/{i}"}
                for i in range(limit)
            ]
        }
    
    @staticmethod
    def get_current_time() -> Dict[str, Any]:
        """Get current time and date"""
        from datetime import datetime
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "timezone": "UTC"
        }
    
    @staticmethod
    def calculate(expression: str) -> Dict[str, Any]:
        """Evaluate mathematical expression"""
        try:
            result = eval(expression)  # In production, use safer evaluation
            return {"result": result, "expression": expression}
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")
    
    @staticmethod
    async def send_reminder(
        message: str,
        delay_seconds: int,
        user_id: str
    ) -> Dict[str, Any]:
        """Create a reminder"""
        # Placeholder: integrate with reminder system
        return {
            "reminder_id": f"reminder_{user_id}_{delay_seconds}",
            "message": message,
            "delay": delay_seconds,
            "status": "scheduled"
        }
    
    @staticmethod
    def set_alarm(time: str, label: str = "") -> Dict[str, Any]:
        """Set an alarm"""
        # Placeholder: integrate with alarm system
        return {
            "alarm_id": f"alarm_{time}",
            "time": time,
            "label": label,
            "status": "set"
        }
    
    @staticmethod
    async def open_app(app_name: str) -> Dict[str, Any]:
        """Open an application (Android integration)"""
        # Placeholder: integrate with Android automation
        return {
            "app": app_name,
            "status": "opening",
            "message": f"Opening {app_name}..."
        }
    
    @staticmethod
    def check_weather(location: str) -> Dict[str, Any]:
        """Check weather for location"""
        # Placeholder: integrate with weather API
        return {
            "location": location,
            "temperature": "25°C",
            "condition": "Sunny",
            "humidity": "65%"
        }
    
    @staticmethod
    async def compose_message(
        recipient: str,
        content: str,
        message_type: str = "sms"  # sms, email, whatsapp
    ) -> Dict[str, Any]:
        """Compose and send a message"""
        # Placeholder: integrate with messaging services
        return {
            "to": recipient,
            "content": content,
            "type": message_type,
            "status": "sent"
        }


def create_default_tool_executor() -> ToolExecutor:
    """Create executor with default tools"""
    executor = ToolExecutor()
    
    # Register default tools
    tools_config = [
        (
            DefaultTools.web_search,
            ToolDefinition(
                name="web_search",
                description="Search the web for information",
                category=ToolCategory.SEARCH,
                parameters=[
                    ToolParameter("query", "Search query", "string", required=True),
                    ToolParameter("limit", "Number of results", "integer", required=False, default=5),
                ]
            )
        ),
        (
            DefaultTools.get_current_time,
            ToolDefinition(
                name="get_current_time",
                description="Get current time and date",
                category=ToolCategory.SYSTEM,
                parameters=[]
            )
        ),
        (
            DefaultTools.calculate,
            ToolDefinition(
                name="calculate",
                description="Evaluate mathematical expression",
                category=ToolCategory.SYSTEM,
                parameters=[
                    ToolParameter("expression", "Math expression to evaluate", "string", required=True),
                ]
            )
        ),
        (
            DefaultTools.send_reminder,
            ToolDefinition(
                name="send_reminder",
                description="Create a reminder for later",
                category=ToolCategory.AUTOMATION,
                parameters=[
                    ToolParameter("message", "Reminder message", "string", required=True),
                    ToolParameter("delay_seconds", "Delay in seconds", "integer", required=True),
                    ToolParameter("user_id", "User ID", "string", required=True),
                ]
            )
        ),
        (
            DefaultTools.set_alarm,
            ToolDefinition(
                name="set_alarm",
                description="Set an alarm clock",
                category=ToolCategory.AUTOMATION,
                parameters=[
                    ToolParameter("time", "Alarm time (HH:MM format)", "string", required=True),
                    ToolParameter("label", "Alarm label", "string", required=False),
                ]
            )
        ),
        (
            DefaultTools.open_app,
            ToolDefinition(
                name="open_app",
                description="Open an application on Android",
                category=ToolCategory.ANDROID,
                parameters=[
                    ToolParameter("app_name", "Application name", "string", required=True),
                ],
                requires_permission="android:execute"
            )
        ),
        (
            DefaultTools.check_weather,
            ToolDefinition(
                name="check_weather",
                description="Check weather for a location",
                category=ToolCategory.KNOWLEDGE,
                parameters=[
                    ToolParameter("location", "City or location", "string", required=True),
                ]
            )
        ),
        (
            DefaultTools.compose_message,
            ToolDefinition(
                name="compose_message",
                description="Send a message to someone",
                category=ToolCategory.MESSAGING,
                parameters=[
                    ToolParameter("recipient", "Recipient phone/email", "string", required=True),
                    ToolParameter("content", "Message content", "string", required=True),
                    ToolParameter("message_type", "SMS, email, or whatsapp", "string", required=False, 
                                 enum_values=["sms", "email", "whatsapp"]),
                ],
                requires_permission="messaging:send"
            )
        ),
    ]
    
    for func, definition in tools_config:
        executor.register_tool(func, definition)
    
    return executor
