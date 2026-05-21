# Sexта-Feira OS - Sprint 2: The Awakening
## Enterprise-Grade AI Assistant Backend - Architecture & Implementation

### 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Core Layers](#core-layers)
3. [AI Gateway](#ai-gateway)
4. [Memory System](#memory-system)
5. [Event-Driven Architecture](#event-driven-architecture)
6. [Security & Authorization](#security--authorization)
7. [API Endpoints](#api-endpoints)
8. [Running the System](#running-the-system)

---

## Architecture Overview

### Clean Architecture + DDD + Event-Driven

```
┌─────────────────────────────────────────────────────┐
│              API Layer (FastAPI)                     │
│  ├─ REST Endpoints (/api/v2/*)                      │
│  ├─ WebSocket Streaming                             │
│  └─ Middleware (Security, Telemetry, CORS)          │
├─────────────────────────────────────────────────────┤
│          Application Layer (Use Cases)               │
│  ├─ SendMessageUseCase                              │
│  ├─ CreateMemoryUseCase                             │
│  ├─ SearchMemoryUseCase                             │
│  └─ DTOs & Interfaces                               │
├─────────────────────────────────────────────────────┤
│          Domain Layer (Business Logic)               │
│  ├─ Entities (UserProfile, Conversation, Message)   │
│  ├─ Value Objects (UserId, Email, MessageContent)   │
│  ├─ Aggregates (Automation, Memory)                 │
│  └─ Repository Interfaces                           │
├─────────────────────────────────────────────────────┤
│      Infrastructure Layer (Implementation)           │
│  ├─ AI Gateway (Provider abstraction)                │
│  ├─ Memory Service (Semantic search, embeddings)     │
│  ├─ Repositories (SQL implementation)                │
│  ├─ Event Handlers                                   │
│  └─ WebSocket Manager                               │
├─────────────────────────────────────────────────────┤
│          Core Layer (Cross-Cutting Concerns)         │
│  ├─ Exceptions (structured error handling)           │
│  ├─ Events (event-driven architecture)               │
│  ├─ Security (RBAC, audit logging)                   │
│  ├─ Telemetry (metrics, health checks)               │
│  ├─ Logging (structured, correlation IDs)            │
│  ├─ Config (environment management)                  │
│  └─ Middleware (request processing)                  │
├─────────────────────────────────────────────────────┤
│          Database Layer (Persistence)                │
│  ├─ SQLAlchemy ORM                                   │
│  ├─ SQLite (development)                             │
│  ├─ PostgreSQL (production)                          │
│  └─ AsyncIO Support                                  │
└─────────────────────────────────────────────────────┘
```

---

## Core Layers

### 1. **Core Layer** (`app/core/`)
Implements cross-cutting concerns:

- **exceptions.py**: Structured exception hierarchy with error codes
  - `SextaFeiraException` (base)
  - `AuthenticationException`, `AIProviderException`, `MemoryException`
  - Auto-serializable to API responses

- **events.py**: Event-driven architecture
  - `DomainEvent` (base event class)
  - `EventBus` (pub/sub pattern)
  - 20+ domain events (USER_CREATED, MESSAGE_SENT, AI_REQUEST_COMPLETED, etc.)
  - Event subscribers can hook into business events

- **security.py**: RBAC + Audit logging
  - Role-based access control (SUPER_ADMIN, ADMIN, MODERATOR, POWER_USER, USER, GUEST)
  - Permission-based authorization
  - `AuditLogger` for compliance tracking
  - `RateLimiter` for API protection

- **logging.py**: Structured logging
  - JSON logging format
  - Correlation IDs for request tracing
  - Context variables for user ID tracking
  - `StructuredLogger` wrapper

- **telemetry.py**: Observability
  - `MetricsCollector` (counters, gauges, histograms, timers)
  - `HealthCheckResult` for service status
  - `ServiceMetrics` for uptime tracking

- **config.py**: Environment configuration
  - 100+ configurable parameters
  - Support for multiple deployment modes
  - Feature flags for gradual rollout

- **middleware.py**: Request processing
  - Correlation ID injection
  - Telemetry collection
  - Security headers
  - Rate limiting
  - Error handling

### 2. **Domain Layer** (`app/domain/`)
Business logic and domain models:

- **entities.py**: DDD entities and aggregates
  - `UserProfile` (aggregate root)
  - `Conversation` (aggregate root with messages)
  - `Message` (entity)
  - `MemoryEntry` (entity)
  - `Automation` (aggregate root)
  - Value objects: `UserId`, `Email`, `MessageContent`, `AIResponse`, `EmbeddingVector`

- **repositories.py**: Repository interfaces (contracts)
  - `UserRepository`
  - `ConversationRepository`
  - `MemoryRepository`
  - `AutomationRepository`
  - `UnitOfWork` pattern for transactions

### 3. **Application Layer** (`app/application/`)
Use cases and DTOs:

- **DTOs** (Data Transfer Objects):
  - `CreateUserDTO`, `UserResponseDTO`
  - `SendMessageDTO`, `MessageResponseDTO`
  - `CreateMemoryDTO`, `MemoryResponseDTO`
  - `SearchMemoryDTO`, `SearchResultDTO`

- **Use Cases** (interfaces):
  - `CreateUserUseCase`
  - `SendMessageUseCase`
  - `GetConversationUseCase`
  - `CreateMemoryUseCase`
  - `SearchMemoryUseCase`

### 4. **Infrastructure Layer** (`app/infrastructure/`)
Technical implementations:

- **AI Gateway** (`ai/`)
  - `BaseAIProvider` (abstract base)
  - `GeminiProvider` (Google Gemini)
  - `AIGateway` (intelligent routing)
  - Features:
    - Automatic fallback between providers
    - Cost-aware routing
    - Latency-aware routing
    - Streaming support
    - Rate limit handling

- **Memory System** (`memory/`)
  - `EmbeddingProvider` (abstract)
  - `SentenceTransformerEmbedding` (local embeddings)
  - `VectorStore` interface
  - `InMemoryVectorStore` (development)
  - `MemoryService` (orchestrator)
  - Features:
    - Semantic search with cosine similarity
    - Hierarchical context injection
    - Memory relevance scoring
    - Automatic summarization

- **WebSocket Manager** (`websocket/`)
  - `ConnectionManager`
  - Features:
    - Real-time connection management
    - Token streaming
    - Error broadcasting
    - Per-user connection limits

- **Event Handlers** (`events/`)
  - `TelemetryEventHandler`
  - `AuditEventHandler`
  - `NotificationEventHandler`
  - `MemoryEnrichmentHandler`

---

## AI Gateway

Advanced provider abstraction layer with intelligent routing:

### Providers
- **Google Gemini** (primary) - Fast, capable, free tier available
- **OpenAI GPT-4** (fallback)
- **Claude 3 Opus** (fallback)
- **Ollama** (local execution)

### Routing Strategies
```python
RoutingStrategy = Enum([
    "COST_OPTIMIZED",      # Minimize API costs
    "LATENCY_OPTIMIZED",   # Fastest response
    "QUALITY_OPTIMIZED",   # Best quality output
    "BALANCED",            # Mix of all factors
    "ROUND_ROBIN",         # Distribute load
    "FALLBACK_CHAIN",      # Try providers in order
])
```

### Example Usage
```python
from app.infrastructure.ai import ai_gateway, AIRequest, ProviderType

request = AIRequest(
    messages=[
        {"role": "user", "content": "What is machine learning?"}
    ],
    system_prompt="You are a helpful AI assistant.",
    temperature=0.7,
    max_tokens=2000,
)

response = await ai_gateway.generate(
    request,
    preferred_provider=ProviderType.GEMINI,
)

# With streaming
async for token in ai_gateway.stream_generate(request):
    print(token, end="")
```

---

## Memory System

Semantic memory with embeddings and hierarchical context:

### Memory Types
```python
MemoryCategoryType = Enum([
    "PROFILE",       # User profile info
    "PREFERENCES",   # User preferences
    "HABITS",        # User behavior patterns
    "INTERACTIONS",  # Chat history summaries
    "AUTOMATION",    # Automation rules
    "CONTEXT",       # Contextual information
    "GENERAL",       # Miscellaneous
])
```

### Semantic Search
```python
from app.infrastructure.memory import memory_service
from app.domain.entities import UserId

# Search memories semantically
results = await memory_service.search_semantic(
    user_id=UserId("user123"),
    query="I like coffee in the morning",
    limit=5,
    min_similarity=0.5,
)

# Inject context into AI requests
context = await memory_service.inject_context(
    user_id=UserId("user123"),
    query="What should I do today?",
    limit=5,
)

# Build personalized system prompt
system_prompt = await memory_service.build_system_prompt(
    user_id=UserId("user123"),
    base_prompt="You are a helpful assistant.",
)
```

### Features
- **Vector Embeddings**: Sentence Transformer models (local)
- **Semantic Search**: Cosine similarity matching
- **Relevance Scoring**: Combines recency + importance
- **Context Injection**: Automatic memory augmentation for AI
- **Summarization**: Compress memory for context windows

---

## Event-Driven Architecture

Domain events trigger side effects without coupling:

### Event Types
```python
EventType = Enum([
    # User events
    "USER_CREATED",
    "USER_AUTHENTICATED",
    "USER_DELETED",
    
    # Message events
    "MESSAGE_SENT",
    "MESSAGE_RECEIVED",
    
    # AI events
    "AI_REQUEST_STARTED",
    "AI_REQUEST_COMPLETED",
    "AI_REQUEST_FAILED",
    "AI_PROVIDER_SWITCHED",
    
    # Memory events
    "MEMORY_CREATED",
    "MEMORY_UPDATED",
    "MEMORY_INDEXED",
    
    # Automation events
    "AUTOMATION_TRIGGERED",
    "AUTOMATION_EXECUTED",
    "AUTOMATION_FAILED",
])
```

### Example: Publishing Events
```python
from app.core.events import publish_event, MessageSentEvent

event = MessageSentEvent(
    message_id="msg123",
    user_id="user456",
    content="Hello, AI!",
)
await publish_event(event)

# Handlers automatically:
# 1. Record telemetry
# 2. Log audit trail
# 3. Send notifications
# 4. Enrich memory
```

---

## Security & Authorization

### Role-Based Access Control
```python
Role = Enum([
    "SUPER_ADMIN",   # All permissions
    "ADMIN",         # User management + audit
    "MODERATOR",     # Chat moderation + audit
    "POWER_USER",    # Enhanced automation + analytics
    "USER",          # Standard user access
    "GUEST",         # Read-only access
])
```

### Permissions
```python
Permission = Enum([
    "USER_CREATE", "USER_READ", "USER_UPDATE", "USER_DELETE",
    "CHAT_READ", "CHAT_WRITE", "CHAT_DELETE",
    "MEMORY_READ", "MEMORY_WRITE", "MEMORY_DELETE",
    "AUTOMATION_READ", "AUTOMATION_WRITE", "AUTOMATION_DELETE", "AUTOMATION_EXECUTE",
    "ADMIN_READ", "ADMIN_WRITE", "SYSTEM_CONFIG",
    "AUDIT_LOG", "ANALYTICS_READ", "ANALYTICS_EXPORT",
])
```

### Audit Logging
```python
from app.core.security import audit_logger

audit_logger.log_action(
    user_id="user123",
    action="DELETE",
    resource_type="MESSAGE",
    resource_id="msg456",
    status="success",
    ip_address="192.168.1.1",
)
```

### Rate Limiting
```python
# Automatically enforced per role
# SUPER_ADMIN: 10k req/min
# ADMIN: 5k req/min
# USER: 500 req/min
# GUEST: 100 req/min
```

---

## API Endpoints

### Health & Status
```
GET  /                           # Root info
GET  /api/v2/health              # Health check
GET  /api/v2/metrics             # System metrics
GET  /api/v2/status              # Detailed status
```

### Authentication (v1)
```
POST /api/v1/auth/register       # User registration
POST /api/v1/auth/login          # User login
POST /api/v1/auth/refresh        # Refresh token
```

### Chat (v1)
```
POST /api/v1/chat/               # Send message
GET  /api/v1/chat/history        # Get conversation
WS   /ws/chat/user/{user_id}     # WebSocket streaming
```

### Memory (v1)
```
POST /api/v1/memory/             # Create memory
GET  /api/v1/memory/             # Get user memory
GET  /api/v1/memory/{memory_id}  # Get specific
DELETE /api/v1/memory/{memory_id} # Delete
POST /api/v1/memory/search       # Semantic search
```

---

## Running the System

### Prerequisites
```bash
# Python 3.10+
python --version

# API Keys
export GEMINI_API_KEY="your-key"
export OPENAI_API_KEY="your-key"  # optional
```

### Installation
```bash
cd backend-core

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-enterprise.txt

# Or basic requirements
pip install -r requirements.txt
```

### Configuration
```bash
# Copy environment template
cp ../.env.example-v2 ../.env

# Edit with your settings
nano ../.env
```

### Run Development Server
```bash
# Using updated main
uvicorn app.main-enterprise:app --reload --port 8000

# Or original
uvicorn app.main:app --reload --port 8000
```

### Run with Docker Compose
```bash
cd ..
docker-compose up -d

# Logs
docker-compose logs -f backend
```

### Health Check
```bash
curl http://localhost:8000/api/v2/health
```

---

## Project Structure - Sprint 2

```
backend-core/
├── app/
│   ├── core/
│   │   ├── exceptions.py          # ✨ Structured exception hierarchy
│   │   ├── events.py              # ✨ Event-driven architecture
│   │   ├── security.py            # ✨ RBAC + Audit logging
│   │   ├── logging.py             # ✨ Structured logging
│   │   ├── telemetry.py           # ✨ Observability metrics
│   │   ├── config.py              # ✨ Enhanced configuration
│   │   ├── middleware.py          # ✨ Request processing
│   │   └── lifecycle.py
│   │
│   ├── domain/                    # ✨ DDD Domain Layer
│   │   ├── entities.py
│   │   ├── repositories.py
│   │   └── __init__.py
│   │
│   ├── application/               # ✨ Use Cases Layer
│   │   ├── __init__.py
│   │   └── (use case implementations)
│   │
│   ├── infrastructure/            # ✨ Infrastructure Layer
│   │   ├── ai/
│   │   │   ├── __init__.py        # AI Gateway
│   │   │   ├── providers/
│   │   │   └── orchestrator.py
│   │   ├── memory/
│   │   │   └── __init__.py        # Memory System
│   │   ├── websocket/
│   │   │   └── __init__.py        # WebSocket Manager
│   │   ├── events/
│   │   │   └── __init__.py        # Event Handlers
│   │   ├── repositories/
│   │   ├── providers/
│   │   └── (other services)
│   │
│   ├── api/
│   │   ├── dependencies.py        # ✨ Dependency Injection
│   │   ├── routers/
│   │   ├── middleware/
│   │   └── websocket/
│   │
│   ├── db/
│   │   ├── database.py
│   │   └── migrations/
│   │
│   ├── models/
│   │   └── models.py              # SQLAlchemy models
│   │
│   ├── schemas/
│   │   └── schemas.py             # Pydantic schemas
│   │
│   ├── services/
│   │   └── memory_service.py
│   │
│   ├── main.py                    # Original main
│   └── main-enterprise.py         # ✨ New enterprise main
│
├── requirements.txt
├── requirements-enterprise.txt     # ✨ Full dependencies
├── Dockerfile
└── README.md
```

---

## Next Steps

### Phase 2: Voice & Vision
- [ ] STT Integration (Whisper)
- [ ] TTS Integration (Edge-TTS)
- [ ] Screen Recording
- [ ] OCR Processing
- [ ] Gesture Recognition

### Phase 3: Automation Engine
- [ ] Task Scheduler
- [ ] Action Registry
- [ ] Workflow Engine
- [ ] Android Integration
- [ ] System Commands

### Phase 4: Advanced Memory
- [ ] ChromaDB Integration
- [ ] FAISS Vector Store
- [ ] LLM-based Summarization
- [ ] Temporal Memory
- [ ] Associative Memory

### Phase 5: Mobile Integration
- [ ] Kotlin API Client (Retrofit)
- [ ] Real-time Sync
- [ ] Offline Capabilities
- [ ] Push Notifications

---

## Key Technologies

| Layer | Technology | Version |
|-------|-----------|---------|
| API | FastAPI | 0.104+ |
| Server | Uvicorn | 0.24+ |
| Database | SQLAlchemy | 2.0+ |
| AI | Google Gemini | latest |
| Embeddings | Sentence Transformers | 2.2+ |
| Auth | JWT (python-jose) | 3.3+ |
| Async | AsyncIO | Python 3.10+ |
| Logging | JSON Logger | 2.0+ |
| Metrics | Prometheus | custom |

---

## Performance Targets

- **Response Time**: < 200ms (50th percentile)
- **AI Response**: < 2s (streaming starts immediately)
- **Memory Search**: < 50ms
- **Uptime**: 99.9%
- **API Availability**: 99.5%
- **Error Rate**: < 0.1%

---

## License

MIT License - See LICENSE file

---

**Sprint 2: The Awakening** - Making the system functional and connected ✨
