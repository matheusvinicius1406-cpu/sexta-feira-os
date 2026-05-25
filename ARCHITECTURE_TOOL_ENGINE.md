# Sexта-Feira OS - Modular Tool Engine Architecture

## Overview

This document describes the refactored tool execution engine architecture for Sexта-Feira OS. The system has been reorganized into clean, modular layers following SOLID principles, Clean Architecture, and Domain-Driven Design patterns.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                              │
│                     (app/main.py - Entry Point)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                          API Layer                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  app/api/tool_router.py - REST Endpoints                        │  │
│  │  ├─ GET /api/v2/tools/list        - List available tools       │  │
│  │  ├─ GET /api/v2/tools/categories  - Get categories             │  │
│  │  ├─ GET /api/v2/tools/schema/{name} - Get tool schema          │  │
│  │  ├─ POST /api/v2/tools/execute    - Execute single tool        │  │
│  │  ├─ POST /api/v2/tools/execute-chain - Execute tool chain      │  │
│  │  └─ GET /api/v2/tools/statistics  - Get execution stats        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                        Schemas Layer                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  app/schemas/tool_schemas.py - Pydantic Models                  │  │
│  │  ├─ ToolListResponse         - List response                    │  │
│  │  ├─ ToolExecutionRequest     - Execution request                │  │
│  │  ├─ ToolExecutionResponse    - Execution response               │  │
│  │  ├─ ToolChainRequest/Response - Tool chain models               │  │
│  │  └─ ToolStatisticsResponse   - Stats model                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                      Application Services Layer                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  app/services/tool_execution_service.py                         │  │
│  │  ├─ execute_tool_in_context()   - Execute with context          │  │
│  │  ├─ execute_tool_chain()        - Execute sequential tools      │  │
│  │  ├─ get_tool_availability()     - List available tools          │  │
│  │  └─ get_execution_summary()     - Get user statistics           │  │
│  │                                                                   │  │
│  │  app/services/conversation_tool_pipeline.py                     │  │
│  │  ├─ process_response_with_tools() - Handle AI tool calls       │  │
│  │  └─ process_conversation_with_tools() - Full conversation       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                   Tool Engine Core Layer                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  app/tools/executor.py - Tool Executor                          │  │
│  │  ├─ execute()            - Execute tool with timeout            │  │
│  │  ├─ list_tools()         - List available tools                 │  │
│  │  └─ get_statistics()     - Execution statistics                 │  │
│  │                                                                   │  │
│  │  app/tools/resolver.py - Tool Resolver                          │  │
│  │  ├─ resolve()            - Resolve tool definition              │  │
│  │  ├─ resolve_handler()    - Get tool handler                     │  │
│  │  ├─ validate_parameters() - Validate inputs                     │  │
│  │  └─ resolve_by_category() - Filter by category                  │  │
│  │                                                                   │  │
│  │  app/tools/registry.py - Tool Registry                          │  │
│  │  ├─ register()          - Register new tool                     │  │
│  │  ├─ get()               - Get tool definition                   │  │
│  │  ├─ get_all()           - Get all tools                         │  │
│  │  └─ get_by_category()   - Filter tools                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                    Android Intent System                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  app/android/intent_service.py - Intent Service                 │  │
│  │  ├─ process_intent()        - Process single intent             │  │
│  │  ├─ process_intents_batch() - Process batch intents             │  │
│  │  └─ register_response_handler() - Register callbacks             │  │
│  │                                                                   │  │
│  │  app/android/dispatcher.py - Intent Dispatcher                  │  │
│  │  ├─ dispatch()              - Route intent to handler           │  │
│  │  ├─ register_handler()      - Register action handler           │  │
│  │  └─ register_type_handler() - Register type handler             │  │
│  │                                                                   │  │
│  │  app/android/intent_builder.py - Fluent Builder                │  │
│  │  ├─ action()                - Set intent action                 │  │
│  │  ├─ payload()               - Set intent payload                │  │
│  │  └─ build()                 - Construct intent                  │  │
│  │                                                                   │  │
│  │  app/android/models.py - Data Models                            │  │
│  │  ├─ AndroidIntent           - Intent data model                 │  │
│  │  ├─ AndroidResponse         - Response model                    │  │
│  │  └─ IntentType/Priority     - Enums                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Module Descriptions

### 1. **Tool System** (`app/tools/`)

The core tool execution engine provides tool discovery, validation, and execution.

#### `registry.py` - Tool Registry
- **Purpose**: Central registry for all tool definitions
- **Key Classes**:
  - `ToolCategory`: Enum for tool categorization
  - `ToolParameter`: Defines tool parameters with types and validation
  - `ToolDefinition`: Complete tool metadata and OpenAI schema generation
  - `ToolRegistry`: Manages all registered tools
- **Pattern**: Singleton (via `get_registry()`)
- **Responsibility**: Tool registration, lookup, and filtering

#### `resolver.py` - Tool Resolver
- **Purpose**: Resolves tool names to definitions and handlers
- **Key Classes**:
  - `ToolResolver`: Routes tool names to implementations
  - `ToolResolutionError`: Custom exception for resolution failures
- **Features**:
  - Parameter validation against tool definition
  - Type checking and conversion
  - Dependency resolution (extensible for tool chains)
- **Pattern**: Dependency Injection

#### `executor.py` - Tool Executor
- **Purpose**: Executes tools with comprehensive error handling
- **Key Classes**:
  - `ToolExecutor`: Command pattern implementation for tool execution
  - `ExecutionResult`: Captures execution outcome and metrics
  - `ExecutionError`: Tool execution exception
- **Features**:
  - Async/sync handler support
  - Timeout management
  - Execution history tracking
  - Statistics collection
- **Safety**: Thread-safe execution with proper error handling

---

### 2. **Services** (`app/services/`)

High-level business logic services built on the tool engine.

#### `tool_execution_service.py` - Tool Execution Service
- **Purpose**: Manages tool execution workflows within conversation context
- **Key Features**:
  - Execute tools with conversation context
  - Sequential tool chain execution
  - User-based tool availability (extensible for RBAC)
  - Execution summary and audit logging
- **Integrations**: Works with conversation context and user sessions

#### `conversation_tool_pipeline.py` - Conversation Tool Pipeline
- **Purpose**: Integrates tool calls into conversation flow
- **Key Features**:
  - Extract tool calls from AI responses (OpenAI compatible)
  - Execute extracted tools automatically
  - Merge results back into conversation
  - Support multiple AI provider response formats
- **Use Case**: Seamless AI-driven tool execution

---

### 3. **Android Intent System** (`app/android/`)

Mobile-specific intent routing and action handling.

#### `models.py` - Data Models
- **Purpose**: Defines Android intent and response models
- **Key Classes**:
  - `AndroidIntent`: Mobile request model with priority/timeout
  - `AndroidResponse`: Mobile response model
  - `IntentType`: Types of intents (voice, UI, automation, etc.)
  - `IntentPriority`: Priority levels (low/normal/high/critical)
- **Features**: Serializable to/from JSON for API communication

#### `intent_builder.py` - Fluent Builder
- **Purpose**: Type-safe intent construction
- **Features**:
  - Fluent API for building intents
  - Convenience methods (e.g., `voice_command()`)
  - Auto-generated request IDs
  - Validation on build
- **Pattern**: Builder pattern for complex object construction

#### `dispatcher.py` - Intent Dispatcher
- **Purpose**: Routes intents to appropriate handlers
- **Features**:
  - Action-specific handlers
  - Intent-type handlers
  - Timeout management
  - Execution tracking
- **Pattern**: Strategy pattern with handler registry

#### `intent_service.py` - Intent Service
- **Purpose**: High-level intent processing
- **Features**:
  - Batch intent processing
  - Response callback handling
  - Intent validation
  - User-based access control (extensible)

---

### 4. **API Layer** (`app/api/`)

RESTful API endpoints for the tool system.

#### `tool_router.py` - Tool Router
- **Purpose**: FastAPI router for tool management endpoints
- **Endpoints**:
  - `GET /api/v2/tools/list` - List tools with filtering
  - `GET /api/v2/tools/categories` - List categories
  - `GET /api/v2/tools/schema/{name}` - Get tool OpenAI schema
  - `POST /api/v2/tools/execute` - Execute single tool
  - `POST /api/v2/tools/execute-chain` - Execute tool sequence
  - `GET /api/v2/tools/statistics` - Execution stats
- **Security**: Requires authentication via `get_current_user`
- **Response Models**: Typed responses via Pydantic schemas

---

### 5. **Schemas** (`app/schemas/`)

Pydantic models for request/response validation.

#### `tool_schemas.py` - Tool Schemas
- **Purpose**: Type-safe request/response models
- **Key Models**:
  - `ToolListResponse` - Typed tool listing
  - `ToolExecutionRequest/Response` - Execution models
  - `ToolChainRequest/Response` - Chain execution
  - `ToolStatisticsResponse` - Stats model
- **Benefits**:
  - Automatic API documentation
  - Request validation
  - Response serialization
  - Type hints for IDEs

---

## Data Flow Examples

### Example 1: Simple Tool Execution

```
Client
  │
  ├─> POST /api/v2/tools/execute
  │   ├─> tool_router.execute_tool()
  │   │   ├─> get_container().tool_executor.execute()
  │   │   │   ├─> resolver.resolve(tool_name)
  │   │   │   ├─> resolver.validate_parameters()
  │   │   │   ├─> resolver.resolve_handler()
  │   │   │   ├─> handler(**parameters)  [with timeout]
  │   │   │   └─> ExecutionResult
  │   │   └─> ToolExecutionResponse
  │
  └─> Response with result/error
```

### Example 2: Tool Chain Execution

```
Client
  │
  ├─> POST /api/v2/tools/execute-chain
  │   ├─> tool_router.execute_tool_chain()
  │   │   ├─> tool_execution_service.execute_tool_chain()
  │   │   │   ├─> For each tool in chain:
  │   │   │   │   ├─> executor.execute(tool_name, params)
  │   │   │   │   └─> collect result
  │   │   │   └─> ToolChainResponse
  │   │   
  │   └─> Return aggregated results
  │
  └─> Response with all results
```

### Example 3: Android Intent Processing

```
Mobile Device
  │
  ├─> WebSocket/REST: AndroidIntent
  │   ├─> IntentService.process_intent()
  │   │   ├─> IntentBuilder.build() [validate]
  │   │   ├─> IntentDispatcher.dispatch()
  │   │   │   ├─> Lookup handler for action
  │   │   │   ├─> handler(intent)
  │   │   │   └─> AndroidResponse
  │   │   ├─> Call response callbacks
  │   │   
  │   └─> AndroidResponse
  │
  └─> Send response to device
```

### Example 4: AI-Driven Tool Execution

```
User → Chat API
  │
  ├─> Conversation with AI
  │   ├─> AI Provider generates response with tool_calls
  │   │
  │   ├─> ConversationToolPipeline.process_response_with_tools()
  │   │   ├─> Extract tool_calls from AI response
  │   │   ├─> For each tool_call:
  │   │   │   ├─> ToolExecutionService.execute_tool_in_context()
  │   │   │   └─> collect result
  │   │   ├─> Merge results into response
  │   │   
  │   └─> Enhanced response with tool results
  │
  └─> Return to user
```

---

## Design Patterns Used

### 1. **Registry Pattern** (`tools/registry.py`)
- Centralized tool registration and discovery
- Enables dynamic tool loading

### 2. **Resolver Pattern** (`tools/resolver.py`)
- Dependency resolution for tools
- Parameter validation and type checking

### 3. **Command Pattern** (`tools/executor.py`)
- Encapsulates tool execution as objects
- Supports queuing, logging, and undo (extensible)

### 4. **Strategy Pattern** (`android/dispatcher.py`)
- Multiple handler strategies for intent routing
- Extensible for different intent types

### 5. **Builder Pattern** (`android/intent_builder.py`)
- Type-safe construction of complex objects
- Fluent API for convenience

### 6. **Singleton Pattern** (`tools/registry.py`)
- Global registry instance via `get_registry()`
- Ensures single source of truth

### 7. **Facade Pattern** (`services/*.py`)
- High-level interfaces over tool engine
- Simplifies complex operations

---

## Integration Points

### With Core DI Container

```python
# In app/core/di.py
container.tool_executor = ToolExecutor()
container.tool_execution_service = ToolExecutionService(container.tool_executor)
container.conversation_pipeline = ConversationToolPipeline(
    container.tool_execution_service
)
```

### With FastAPI Application

```python
# In app/main.py
from app.api import tool_router
app.include_router(tool_router.router)
```

### With Conversation Flow

```python
# In conversation handlers
result = await conversation_tool_pipeline.process_response_with_tools(
    ai_response=ai_output,
    user_id=user_id,
    conversation_id=conversation_id,
)
```

---

## Security Considerations

1. **Authentication**: All endpoints require `get_current_user` dependency
2. **Parameter Validation**: All parameters validated against tool definitions
3. **Timeout Protection**: All executions have timeout limits
4. **Error Handling**: Comprehensive error handling with sanitized error messages
5. **Audit Logging**: Execution history tracked for compliance
6. **RBAC Ready**: Tool availability can be restricted per user/role

---

## Scalability Features

1. **Async/Await**: Non-blocking execution for high concurrency
2. **Thread Pool**: Sync handlers executed in thread pool
3. **Execution History**: Bounded history with configurable limits
4. **Statistics**: Real-time execution metrics
5. **Extensibility**: Easy to add new tools via registry
6. **Modular Design**: Each layer can be scaled independently

---

## Testing Strategy

### Unit Tests
- Test each registry operation
- Test parameter validation
- Test handler registration/execution
- Test intent building

### Integration Tests
- Test API endpoint chains
- Test tool execution flow
- Test error handling
- Test timeout behavior

### E2E Tests
- Test complete tool execution workflow
- Test AI response tool extraction
- Test Android intent processing
- Test concurrent execution

---

## Future Enhancements

1. **Tool Dependencies**: Model and resolve tool dependencies
2. **Conditional Execution**: If/then logic for tool chains
3. **Parallel Tool Execution**: Run independent tools concurrently
4. **Tool Caching**: Cache expensive tool results
5. **Custom Tool Development**: SDK for community tools
6. **Tool Marketplace**: Publish/discover tools
7. **Advanced Analytics**: Usage patterns and optimization
8. **Tool Composition**: Build complex workflows from simple tools

---

## File Structure

```
backend-core/app/
├── api/
│   ├── __init__.py              (exports tool_router)
│   ├── tool_router.py           ✨ NEW: REST endpoints
│   └── routers/                 (existing routers)
│
├── tools/                        ✨ NEW: Tool execution engine
│   ├── __init__.py
│   ├── registry.py
│   ├── resolver.py
│   └── executor.py
│
├── services/
│   ├── __init__.py              (updated)
│   ├── tool_execution_service.py ✨ NEW
│   ├── conversation_tool_pipeline.py ✨ NEW
│   └── memory_service.py         (existing)
│
├── android/                      ✨ NEW: Intent system
│   ├── __init__.py
│   ├── models.py
│   ├── dispatcher.py
│   ├── intent_builder.py
│   └── intent_service.py
│
├── schemas/
│   ├── __init__.py              (updated)
│   ├── tool_schemas.py          ✨ NEW
│   └── schemas.py               (existing)
│
└── main.py                       (updated)
```

---

## Migration Guide

### For Existing Code

1. **Existing tool routers**: Existing `app/api/routers/tools.py` remains functional
2. **Backward compatible**: New modules don't break existing imports
3. **Gradual migration**: Can coexist with old system during transition

### For New Code

1. Use `app.tools.ToolExecutor` for tool execution
2. Use `app.services.ToolExecutionService` for conversation context
3. Use `app.android.IntentService` for mobile intents
4. Use `app.api.tool_router` for REST API

### DI Integration

```python
# Initialize in app/core/di.py
executor = ToolExecutor()
service = ToolExecutionService(executor)
pipeline = ConversationToolPipeline(service)

container.tool_executor = executor
container.tool_execution_service = service
container.conversation_pipeline = pipeline
```

---

## Conclusion

The refactored tool engine architecture provides:

✅ **Clean Separation of Concerns** - Distinct layers for registry, execution, services
✅ **Type Safety** - Pydantic models and type hints throughout
✅ **Extensibility** - Easy to add new tools and features
✅ **Testability** - Each component can be tested in isolation
✅ **Scalability** - Async-first design ready for high concurrency
✅ **Maintainability** - Clear patterns and well-documented code
✅ **SOLID Principles** - Following SRP, OCP, LSP, ISP, DIP
✅ **FastAPI Compatible** - Seamless integration with existing framework

This architecture sets the foundation for Jarvis-like AI runtime systems and future agent orchestration.
