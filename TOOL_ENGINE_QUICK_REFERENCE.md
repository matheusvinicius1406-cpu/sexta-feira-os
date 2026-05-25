# Quick Reference - Tool Engine Architecture

## Quick Start

### Import Core Components
```python
from app.tools import ToolRegistry, ToolResolver, ToolExecutor
from app.services import ToolExecutionService, ConversationToolPipeline
from app.android import IntentDispatcher, IntentService
from app.schemas import ToolListResponse, ToolExecutionRequest
```

### Create & Register a Tool
```python
from app.tools import ToolDefinition, ToolCategory, ToolParameter, get_registry

# Define tool
tool = ToolDefinition(
    name="send_email",
    description="Send an email message",
    category=ToolCategory.COMMUNICATION,
    parameters=[
        ToolParameter(name="to", type="string", description="Recipient email"),
        ToolParameter(name="subject", type="string", description="Email subject"),
        ToolParameter(name="body", type="string", description="Email body"),
    ],
    requires_confirmation=False,
    timeout_seconds=30,
)

# Register
registry = get_registry()
registry.register(tool)

# Register handler
from app.tools import ToolResolver
resolver = ToolResolver(registry)

async def send_email_handler(to: str, subject: str, body: str):
    # Your implementation
    return {"status": "sent", "message_id": "123"}

resolver.register_handler("send_email", send_email_handler)
```

### Execute a Tool
```python
from app.tools import ToolExecutor

executor = ToolExecutor(resolver)

result = await executor.execute(
    tool_name="send_email",
    parameters={
        "to": "user@example.com",
        "subject": "Hello",
        "body": "Test message",
    },
    user_id="user123",
)

if result.success:
    print(f"Tool executed in {result.execution_time_ms}ms")
    print(f"Result: {result.result}")
else:
    print(f"Error: {result.error}")
```

### Execute Tool Chain
```python
service = ToolExecutionService(executor)

results = await service.execute_tool_chain(
    tools=[
        {
            "tool_name": "get_weather",
            "parameters": {"location": "NYC"},
        },
        {
            "tool_name": "send_notification",
            "parameters": {"message": "Weather update"},
            "fail_on_error": True,
        },
    ],
    user_id="user123",
)
```

### Process Android Intent
```python
from app.android import IntentBuilder, IntentService, IntentType

service = IntentService()

# Build intent
intent = IntentBuilder() \
    .action("SEND_MESSAGE") \
    .intent_type(IntentType.VOICE_COMMAND) \
    .add_payload("message", "Hello world") \
    .device_id("device123") \
    .user_id("user123") \
    .build()

# Process
response = await service.dispatcher.dispatch(intent)

if response.success:
    print(f"Intent processed: {response.data}")
else:
    print(f"Error: {response.error}")
```

### Use in Conversation
```python
from app.services import ConversationToolPipeline

pipeline = ConversationToolPipeline(tool_execution_service)

# AI returns response with tool calls
ai_response = {
    "text": "I found your weather",
    "tool_calls": [
        {
            "name": "get_weather",
            "arguments": {"location": "NYC"},
        }
    ]
}

# Pipeline executes tools and merges results
result = await pipeline.process_response_with_tools(
    ai_response,
    user_id="user123",
    conversation_id="conv456",
)

# Result now has tool execution results
print(result["tool_execution_results"])
```

---

## API Endpoints

### List Tools
```bash
GET /api/v2/tools/list?category=communication
Authorization: Bearer <token>

Response:
{
  "success": true,
  "tools": [
    {
      "name": "send_email",
      "description": "Send an email",
      "category": "communication",
      "parameters": [...],
      "requires_confirmation": false,
      "timeout_seconds": 30
    }
  ],
  "count": 1
}
```

### Get Tool Categories
```bash
GET /api/v2/tools/categories
Authorization: Bearer <token>

Response:
{
  "success": true,
  "categories": [
    "automation",
    "communication",
    "productivity",
    "information",
    "device_control",
    "integration",
    "custom"
  ],
  "count": 7
}
```

### Get Tool Schema (OpenAI compatible)
```bash
GET /api/v2/tools/schema/send_email
Authorization: Bearer <token>

Response:
{
  "success": true,
  "schema": {...},
  "openai_schema": {
    "type": "function",
    "function": {
      "name": "send_email",
      "description": "Send an email",
      "parameters": {...}
    }
  }
}
```

### Execute Tool
```bash
POST /api/v2/tools/execute
Authorization: Bearer <token>
Content-Type: application/json

{
  "tool_name": "send_email",
  "parameters": {
    "to": "user@example.com",
    "subject": "Hello",
    "body": "Test"
  },
  "requires_confirmation": false,
  "timeout_override": 30.0
}

Response:
{
  "success": true,
  "tool_name": "send_email",
  "result": {"status": "sent", "message_id": "123"},
  "execution_time_ms": 145.67,
  "timestamp": "2024-01-15T10:30:00",
  "user_id": "user123"
}
```

### Execute Tool Chain
```bash
POST /api/v2/tools/execute-chain
Authorization: Bearer <token>
Content-Type: application/json

{
  "tools": [
    {
      "tool_name": "get_weather",
      "parameters": {"location": "NYC"}
    },
    {
      "tool_name": "send_email",
      "parameters": {"to": "user@example.com", "subject": "Weather"},
      "fail_on_error": true
    }
  ]
}

Response:
{
  "success": true,
  "tools_executed": {
    "total": 2,
    "successful": 2,
    "failed": 0
  },
  "results": [...],
  "total_execution_time_ms": 456.78
}
```

### Get Statistics
```bash
GET /api/v2/tools/statistics
Authorization: Bearer <token>

Response:
{
  "total": 150,
  "successful": 148,
  "failed": 2,
  "success_rate": 98.67,
  "average_execution_time_ms": 156.45
}
```

---

## Common Patterns

### Pattern 1: Simple Tool Registration
```python
# Define
tool = ToolDefinition(name="my_tool", ...)
registry.register(tool)
resolver.register_handler("my_tool", my_handler)

# Execute
result = await executor.execute("my_tool", {"param": "value"})
```

### Pattern 2: Tool with Multiple Parameters
```python
tool = ToolDefinition(
    name="calculate",
    parameters=[
        ToolParameter("operation", "string", "Add/subtract/multiply", 
                      enum=["add", "subtract", "multiply"]),
        ToolParameter("a", "number", "First number"),
        ToolParameter("b", "number", "Second number"),
    ],
)
```

### Pattern 3: Async Tool Handler
```python
async def fetch_data_handler(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

resolver.register_handler("fetch_data", fetch_data_handler)
```

### Pattern 4: Tool with Confirmation
```python
tool = ToolDefinition(
    name="delete_user",
    requires_confirmation=True,  # Will need user approval
)
```

### Pattern 5: Custom Tool Category
```python
# Extend ToolCategory enum if needed
tool = ToolDefinition(
    name="my_tool",
    category=ToolCategory.CUSTOM,
)
```

---

## Error Handling

### Resolve Errors
```python
from app.tools import ToolResolutionError

try:
    tool = resolver.resolve("nonexistent_tool")
except ToolResolutionError as e:
    print(f"Tool not found: {e}")
```

### Execution Errors
```python
result = await executor.execute("my_tool", {})

if not result.success:
    print(f"Type: {result.error_type}")
    print(f"Message: {result.error}")
    
    # Handle by error type
    if result.error_type == "TimeoutError":
        # Handle timeout
    elif result.error_type == "ResolutionError":
        # Handle missing tool/handler
    else:
        # Handle other errors
```

### Parameter Validation Errors
```python
try:
    resolver.validate_parameters("my_tool", {"wrong": "params"})
except ToolResolutionError as e:
    print(f"Validation failed: {e}")
```

---

## Testing

### Test Tool Execution
```python
import pytest
from app.tools import ToolExecutor, ToolResolver, ToolRegistry

@pytest.fixture
def executor():
    registry = ToolRegistry()
    resolver = ToolResolver(registry)
    return ToolExecutor(resolver)

@pytest.mark.asyncio
async def test_tool_execution(executor):
    # Setup
    async def dummy_handler(): return {"result": "success"}
    
    # Register
    executor.resolver.register_handler("test_tool", dummy_handler)
    
    # Execute
    result = await executor.execute("test_tool", {})
    
    # Assert
    assert result.success
    assert result.result == {"result": "success"}
```

### Test Intent Processing
```python
import pytest
from app.android import IntentService, IntentType

@pytest.mark.asyncio
async def test_intent_processing():
    service = IntentService()
    
    response = await service.process_intent(
        action="TEST_ACTION",
        payload={"key": "value"},
        device_id="device123",
        user_id="user123",
        intent_type=IntentType.UI_ACTION,
    )
    
    # Would fail without registered handler
    assert not response.success
    assert response.error_type == "NoHandlerError"
```

---

## Troubleshooting

### Tool Not Found
```
Error: Tool 'my_tool' not found in registry
→ Check: registry.exists('my_tool')
→ Register: registry.register(tool_definition)
```

### Handler Not Registered
```
Error: Handler for tool 'my_tool' not registered
→ Check: resolver.has_handler('my_tool')
→ Register: resolver.register_handler('my_tool', handler)
```

### Timeout Error
```
Error: Tool execution timeout (30s)
→ Increase: tool.timeout_seconds
→ Or pass: timeout_override=60.0 to executor.execute()
```

### Parameter Validation Failed
```
Error: Missing required parameters for 'my_tool': {'param'}
→ Check: tool.parameters list
→ Provide: all required parameters in execution call
```

### Circular Imports
```
ImportError: circular import detected
→ Use: from app.tools import get_registry()  # Lazy import
→ Or: Import at function scope, not module scope
```

---

## Performance Tips

1. **Reuse Registry**: Don't create new registry instances
2. **Use async**: Use async handlers for I/O operations
3. **Set Timeouts**: Always set appropriate timeouts
4. **Batch Tools**: Use execute_tool_chain for multiple tools
5. **Cache Results**: Cache expensive tool results at service level
6. **Monitor History**: Keep bounded execution history size

---

## Module Map

```
Tool Execution Flow:
Client Request
  ↓
API Router (tool_router.py)
  ↓
Executor (executor.py)
  ├→ Resolver (resolver.py)
  │  ├→ Registry (registry.py)
  │  └→ Validate
  ├→ Handler
  └→ Result

Service Layer:
ConversationToolPipeline
  └→ ToolExecutionService
      └→ ToolExecutor
```

---

## Links

- Full docs: See `ARCHITECTURE_TOOL_ENGINE.md`
- Refactoring summary: See `REFACTORING_SUMMARY.md`
- Source code: `backend-core/app/{tools,services,android,api}/`
