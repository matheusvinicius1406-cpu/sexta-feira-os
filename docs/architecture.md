# Architecture Overview

## System Design

Sexta-Feira OS follows a **clean, layered architecture** with clear separation of concerns across mobile, backend, and shared components.

```
┌─────────────────────────────────────────────────────────────┐
│                      Mobile Client (Android)                │
│  Jetpack Compose UI | Voice Input | Local Storage (Room)    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS + JWT Auth
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                          │
│  ├─ API Layer (REST Routers)                               │
│  ├─ Business Logic (Services)                              │
│  ├─ AI Orchestration (Multi-Provider)                      │
│  ├─ Memory Management                                       │
│  └─ Authentication & Security                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼───┐      ┌──────▼───┐      ┌──────▼────┐
   │PostgreSQL   │ SQLite    │  │ External   │
   │(Production) │(Development)│  │ AI APIs    │
   └────────┘      └──────────┘      └───────────┘
```

## Backend Architecture

### Layered Design

```
app/
├── api/                    # HTTP REST endpoints (routers)
│   └── routers/
│       ├── health.py      # Health checks
│       ├── auth.py        # Authentication
│       ├── chat.py        # Chat/Message endpoints
│       └── memory.py      # Memory/Context endpoints
│
├── core/                   # Configuration & settings
│   └── config.py
│
├── models/                 # SQLAlchemy ORM models
│   └── models.py          # User, ChatMessage, MemoryEntry, etc.
│
├── schemas/               # Pydantic request/response validation
│   └── schemas.py         # DTO objects
│
├── services/              # Business logic layer
│   └── memory_service.py
│
├── auth/                  # Authentication utilities
│   └── jwt.py             # JWT token management
│
├── ai/                    # AI provider abstraction
│   └── orchestrator.py    # Multi-provider routing
│
├── db/                    # Database setup
│   └── database.py
│
└── main.py               # FastAPI application entry point
```

### Data Flow

```
1. Client sends request with JWT token
   ↓
2. FastAPI router receives request
   ↓
3. Authentication middleware validates token
   ↓
4. Request routed to appropriate service
   ↓
5. Service processes business logic
   ↓
6. Database accessed if needed (ORM → SQL)
   ↓
7. Response serialized via Pydantic schema
   ↓
8. JSON response sent to client
```

## Mobile Architecture

### MVVM with Compose

```
UI Layer (Jetpack Compose)
    ↓
ViewModel Layer (StateFlow)
    ↓
Repository Layer (Data abstraction)
    ↓
Data Layer
├─ API Client (Retrofit)
└─ Local Storage (Room)
```

### Package Organization

```
com.sextafeira.os/
├── ui/                    # Presentation layer
│   ├── screens/          # Individual screens
│   ├── components/       # Reusable UI components
│   ├── navigation/       # Compose navigation
│   └── theme/            # Material 3 theme
│
├── viewmodel/            # MVVM ViewModels
│
├── data/                 # Data layer
│   ├── api/             # API client & DTOs
│   ├── local/           # Local storage
│   └── repository/      # Data abstraction
│
├── domain/              # Business logic
│   ├── model/           # Domain models
│   └── usecase/         # Use cases
│
├── di/                  # Dependency injection (Hilt)
│
└── util/                # Utilities & helpers
```

## Authentication Flow

```
1. User enters credentials
   ↓
2. POST /api/v1/auth/login with email + password
   ↓
3. Backend validates credentials
   ↓
4. JWT token generated (exp: 24h)
   ↓
5. Token returned to client
   ↓
6. Stored securely (EncryptedSharedPreferences)
   ↓
7. Included in all subsequent requests as Bearer token
```

## AI Orchestration

```
Client Request (message + provider)
    ↓
AIOrchestrator.process_chat()
    ↓
├─ Check requested provider (OpenAI, Claude, Gemini, etc.)
├─ Validate API key availability
├─ Fetch user context from memory store
│
├─ Route to appropriate provider adapter
│   ├─ OpenAI → OpenAI SDK
│   ├─ Claude → Anthropic SDK
│   └─ Gemini → Google SDK
│
├─ Add system prompt with user context
├─ Generate response
│
└─ Store interaction in memory database
    ↓
Return response to client
```

## Memory & Context Management

```
User Context consists of:
├─ Preferences (dark mode, language, voice speed)
├─ Habits (common queries, patterns)
├─ Recent Interactions (last 10 messages)
├─ Personal Data (name, email, interests)
└─ Automation Rules (scheduled tasks)

Storage:
├─ Persistent DB (PostgreSQL/SQLite) → Long-term
├─ Cache (Redis optional) → Fast access
└─ Local Phone Storage → Offline capability
```

## Security Considerations

- **JWT Tokens**: HS256 signed, 24-hour expiry
- **Password Hashing**: bcrypt with salt
- **CORS**: Configured for specific origins only
- **HTTPS**: Required in production
- **API Keys**: Never logged, environment-only
- **Database**: Prepared statements to prevent SQL injection

## Scalability

- **Async Processing**: FastAPI uses async/await for high concurrency
- **Connection Pooling**: SQLAlchemy + pgbouncer ready
- **Caching Layer**: Redis-ready for hot data
- **Horizontal Scaling**: Stateless design allows load balancing
- **Rate Limiting**: TODO - add rate limiting middleware

## Future Enhancements

- Event-driven architecture with message queue (Kafka/RabbitMQ)
- GraphQL endpoint alongside REST
- Real-time updates via WebSocket
- Voice processing pipeline (audio → text → intent → action)
- Multi-modal support (vision, sensor data from smart glasses)
- Distributed memory across edge devices
