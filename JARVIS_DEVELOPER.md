# 🤖 Jarvis System - Developer Guide

## Architecture Overview

### Core Components

#### 1. **Agent System**
Agents are autonomous entities with specific capabilities and tools.

```python
from app.jarvis import Agent, AgentCapability, Tool

# Create an agent
assistant = Agent(
    id="jarvis-main",
    name="Jarvis",
    description="Main AI assistant",
    capabilities=[
        AgentCapability.CHAT,
        AgentCapability.ANALYSIS,
        AgentCapability.LEARNING,
    ],
    personality="Helpful, intelligent, and friendly",
    system_prompt="You are a personal AI assistant...",
    temperature=0.7,
    max_tokens=2000
)
```

#### 2. **Tool Registry**
Tools are functions that agents can execute.

```python
from app.jarvis import Tool, ToolRegistry

# Define a tool
async def calculate(expression: str) -> str:
    """Evaluate mathematical expression"""
    try:
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"

# Create tool
calculator = Tool(
    name="calculator",
    description="Performs mathematical calculations",
    parameters={"expression": "str"},
    function=calculate,
    enabled=True
)

# Register globally
ToolRegistry.register(calculator)

# Or add to specific agent
assistant.add_tool(calculator)
```

#### 3. **Memory System**
Persistent memory for users and conversations.

```python
from app.jarvis import JarvisMemory

memory = JarvisMemory()

# Store information
memory.store("user_preference_theme", "dark")
memory.store("favorite_music", "jazz")

# Retrieve information
theme = memory.retrieve("user_preference_theme")  # Returns "dark"

# Add interaction history
memory.add_interaction(
    user="Tell me about yourself",
    ai="I'm Jarvis, your personal AI assistant...",
    context={"mood": "curious"}
)

# Get context for conversation
recent_context = memory.get_recent_context(limit=5)
```

#### 4. **Gemini Integration**
Low-level and high-level Gemini provider wrappers.

```python
from app.jarvis import GeminiProvider, GeminiOrchestratorV2

# Low-level provider
provider = GeminiProvider(
    api_key="your-key-here",
    model="gemini-2.0-flash"
)

# Send message
response = await provider.chat(
    message="Hello",
    system_prompt="You are helpful",
    context_history=[]
)

# High-level orchestrator (preferred)
orchestrator = GeminiOrchestratorV2(api_key="your-key-here")

# Process with history management
response = await orchestrator.process_chat(
    user_message="What can you do?",
    user_context={"name": "John", "timezone": "UTC"}
)

# Analyze text
analysis = await orchestrator.analyze_text(
    text="This product is amazing!",
    analysis_type="sentiment"  # or "summary", "keywords", "general"
)

# Stream responses
async for chunk in orchestrator.stream_chat("Tell me a story"):
    print(chunk, end="")
```

---

## Example: Creating a Custom Agent

### Step 1: Define Tools

```python
# File: backend-core/app/jarvis/tools/weather.py

from app.jarvis import Tool
import aiohttp

async def get_weather(city: str) -> str:
    """Get current weather for a city"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.weatherapi.com/v1/current.json?key=KEY&q={city}"
            async with session.get(url) as resp:
                data = await resp.json()
                return f"Weather in {city}: {data['current']['condition']['text']}, {data['current']['temp_c']}°C"
    except Exception as e:
        return f"Could not get weather: {e}"

weather_tool = Tool(
    name="weather",
    description="Get current weather for any city",
    parameters={"city": "str"},
    function=get_weather,
    enabled=True
)
```

### Step 2: Create Agent

```python
# File: backend-core/app/jarvis/agents/weather_agent.py

from app.jarvis import Agent, AgentCapability, AgentRegistry
from app.jarvis.tools.weather import weather_tool

weather_agent = Agent(
    id="agent-weather",
    name="Weather Assistant",
    description="Provides weather information and forecasts",
    capabilities=[
        AgentCapability.CHAT,
        AgentCapability.ANALYSIS,
    ],
    personality="Friendly and informative about weather",
    system_prompt="You are a weather assistant. Use the weather tool to help users.",
    temperature=0.5,
    max_tokens=500
)

# Add tools
weather_agent.add_tool(weather_tool)

# Register globally
AgentRegistry.register(weather_agent)
```

### Step 3: Use in API

```python
# File: backend-core/app/api/routers/weather.py

from fastapi import APIRouter, Depends
from app.jarvis import AgentRegistry
from app.ai.orchestrator import ai_orchestrator

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])

@router.get("/forecast/{city}")
async def get_weather_forecast(city: str):
    """Get weather for a city using Jarvis Weather Agent"""
    
    agent = AgentRegistry.get("agent-weather")
    
    response = await ai_orchestrator.process_chat(
        message=f"What's the weather like in {city}?",
        provider="gemini"
    )
    
    return {
        "city": city,
        "forecast": response.get("response"),
        "agent": agent.name
    }
```

---

## Example: Implementing a Learning System

### 1. Store Feedback

```python
# File: backend-core/app/services/learning_service.py

from app.models.models import MemoryEntry, ChatMessage
from sqlalchemy.orm import Session
from datetime import datetime

class LearningService:
    @staticmethod
    def store_feedback(
        db: Session,
        user_id: str,
        message_id: str,
        feedback: str,  # "good", "bad", "neutral"
        reason: str = None
    ):
        """Store user feedback for learning"""
        
        entry = MemoryEntry(
            user_id=user_id,
            key=f"feedback_{message_id}",
            value=f"feedback={feedback}, reason={reason}",
            category="learning",
            importance=8 if feedback == "bad" else 5,
            created_at=datetime.utcnow()
        )
        db.add(entry)
        db.commit()
```

### 2. Analyze Patterns

```python
def get_user_preferences(db: Session, user_id: str) -> dict:
    """Analyze memory entries to find user preferences"""
    
    memories = db.query(MemoryEntry).filter(
        MemoryEntry.user_id == user_id,
        MemoryEntry.category == "learning"
    ).all()
    
    preferences = {
        "response_tone": "friendly",
        "detail_level": "moderate",
        "preferred_providers": [],
    }
    
    # Analyze feedback patterns
    for memory in memories:
        if "tone" in memory.value:
            # Parse and update preference
            pass
    
    return preferences
```

### 3. Apply in Chat

```python
async def process_chat_with_learning(
    message: str,
    user_id: str,
    db: Session
):
    """Chat with personalized learning"""
    
    # Get user preferences
    prefs = LearningService.get_user_preferences(db, user_id)
    
    # Modify system prompt based on preferences
    system_prompt = f"""You are Jarvis.
    User preferences:
    - Response tone: {prefs['response_tone']}
    - Detail level: {prefs['detail_level']}
    
    Personalize your responses accordingly."""
    
    response = await ai_orchestrator.process_chat(
        message=message,
        custom_system_prompt=system_prompt
    )
    
    return response
```

---

## Example: Tool with Parameters

```python
from app.jarvis import Tool
import json

async def web_search(query: str, limit: int = 5) -> str:
    """Search the web for information"""
    # Mock implementation
    return json.dumps({
        "results": [
            {"title": f"Result {i}", "url": f"https://example.com/{i}"}
            for i in range(limit)
        ]
    })

search_tool = Tool(
    name="web_search",
    description="Search the internet for information",
    parameters={
        "query": "str",  # Search query
        "limit": "int"   # Number of results (default 5)
    },
    function=web_search,
    enabled=True
)
```

---

## API Endpoints for Jarvis System

### Chat
```
POST /api/v1/jarvis/chat
Content-Type: application/json
Authorization: Bearer <token>

{
  "message": "Hello Jarvis",
  "provider": "gemini"
}
```

### Memory Operations
```
POST /api/v1/jarvis/memory/store
?key=name&value=value

GET /api/v1/jarvis/memory/recall
?key=name
```

### System Status
```
GET /api/v1/jarvis/status
```

### Analysis
```
POST /api/v1/jarvis/analyze
?text=text&analysis_type=sentiment
```

---

## Configuration

### Environment Variables

```env
# Gemini API
GEMINI_API_KEY=sk-...

# Jarvis System
JARVIS_SYSTEM_NAME=Jarvis
JARVIS_TEMPERATURE=0.7
JARVIS_MAX_TOKENS=2000
JARVIS_ENABLE_MEMORY=true
JARVIS_ENABLE_LEARNING=true
JARVIS_ENABLE_TOOLS=true
```

### Python Configuration

```python
from app.jarvis import JarvisConfig, JarvisSystem
from app.core.config import settings

config = JarvisConfig(
    gemini_api_key=settings.gemini_api_key,
    model_name="gemini-2.0-flash",
    temperature=settings.jarvis_temperature,
    system_name=settings.jarvis_system_name,
    enable_memory=settings.jarvis_enable_memory,
    enable_learning=settings.jarvis_enable_learning,
    enable_tools=settings.jarvis_enable_tools
)

jarvis = JarvisSystem(config)
```

---

## File Structure

```
backend-core/app/jarvis/
├── __init__.py              # Public API
├── core.py                  # Agent, Tool, Memory classes
├── gemini.py                # Gemini provider
├── agents/                  # Specific agent implementations
│   ├── __init__.py
│   ├── main_assistant.py    # Primary Jarvis agent
│   ├── weather_agent.py     # Example weather agent
│   └── ...
├── tools/                   # Tool implementations
│   ├── __init__.py
│   ├── calculator.py
│   ├── search.py
│   └── ...
└── skills/                  # High-level skills
    ├── __init__.py
    ├── conversation.py
    ├── analysis.py
    └── ...
```

---

## Best Practices

1. **Tool Design**
   - Keep tools focused on a single task
   - Always handle errors gracefully
   - Return structured responses
   - Document parameters clearly

2. **Agent Design**
   - Clear system prompt
   - Specific capabilities
   - Appropriate temperature (0.3-0.9)
   - Tool selection matching capabilities

3. **Memory Management**
   - Store user preferences separately
   - Use categories for organization
   - Set importance levels
   - Regular cleanup of old entries

4. **Async/Await**
   - Use async for all AI operations
   - Proper exception handling
   - Timeout management
   - Stream support where possible

5. **Testing**
   - Unit test individual tools
   - Integration test agent workflows
   - Load test with multiple users
   - Edge case coverage

---

## Debugging

### Enable Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Tool execution details")
logger.info("Agent state changes")
logger.warning("Potential issues")
logger.error("Error occurred")
```

### Check Agent Status

```python
from app.jarvis import AgentRegistry, ToolRegistry

# List all agents
agents = AgentRegistry.list_all()
for agent in agents:
    print(f"Agent: {agent.name}")
    print(f"  Capabilities: {agent.capabilities}")
    print(f"  Tools: {[t.name for t in agent.tools]}")

# List all tools
tools = ToolRegistry.list_all()
for tool in tools:
    print(f"Tool: {tool.name}")
    print(f"  Enabled: {tool.enabled}")
```

### Test Tool Execution

```python
import asyncio

async def test_tool():
    tool = ToolRegistry.get("calculator")
    result = await tool.function("2 + 2")
    print(result)

asyncio.run(test_tool())
```

---

## Contributing

To add new features to Jarvis:

1. Create tool/agent in appropriate module
2. Add tests
3. Update documentation
4. Create API endpoints if needed
5. Submit for review

---

**Jarvis is open for extension and customization!**
