# API Documentation

Base URL: `http://localhost:8000/api/v1`

All requests should include `Content-Type: application/json` header.

## Authentication

### Login
**Endpoint:** `POST /auth/login`

Request:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

Response (200 OK):
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user_id": "uuid",
  "expires_in": 86400
}
```

**Usage:** Include token in subsequent requests:
```
Authorization: Bearer <access_token>
```

### Register
**Endpoint:** `POST /auth/register`

Request:
```json
{
  "email": "newuser@example.com",
  "password": "SecurePassword123",
  "name": "John Doe"
}
```

Response (200 OK):
```json
{
  "id": "user-uuid",
  "email": "newuser@example.com",
  "name": "John Doe",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00"
}
```

## Health & Status

### Health Check
**Endpoint:** `GET /health`

Response (200 OK):
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "database": "connected",
  "timestamp": "2025-01-15T10:30:00"
}
```

## Chat Endpoints

### Send Message
**Endpoint:** `POST /chat`

**Headers:** `Authorization: Bearer <token>`

Request:
```json
{
  "message": "What's the weather like?",
  "provider": "openai",
  "context": {
    "location": "San Francisco",
    "timezone": "PST"
  }
}
```

Response (200 OK):
```json
{
  "id": "message-uuid",
  "content": "It's sunny in San Francisco, around 72°F with light winds.",
  "is_from_assistant": true,
  "ai_provider": "openai",
  "confidence": 0.95,
  "created_at": "2025-01-15T10:30:00"
}
```

### Get Chat History
**Endpoint:** `GET /chat/history?limit=50`

**Headers:** `Authorization: Bearer <token>`

Response (200 OK):
```json
{
  "messages": [
    {
      "id": "msg-1",
      "content": "Hello!",
      "is_from_assistant": false,
      "ai_provider": "openai",
      "confidence": null,
      "created_at": "2025-01-15T10:25:00"
    },
    {
      "id": "msg-2",
      "content": "Hello! How can I help you today?",
      "is_from_assistant": true,
      "ai_provider": "openai",
      "confidence": 0.98,
      "created_at": "2025-01-15T10:25:30"
    }
  ],
  "total_count": 2
}
```

**Query Parameters:**
- `limit` (optional, default: 50): Number of messages to retrieve

## Memory Endpoints

### Get User Memory & Context
**Endpoint:** `GET /memory`

**Headers:** `Authorization: Bearer <token>`

Response (200 OK):
```json
{
  "user_context": {
    "preferences": {
      "voice_speed": "normal",
      "language": "en-US",
      "theme": "dark"
    },
    "habits": {
      "morning_time": "7:30",
      "preferred_assistant": "openai"
    }
  },
  "recent_interactions": [
    "What's on my calendar?",
    "Set a reminder for tomorrow",
    "Tell me about AI"
  ],
  "preferences": {
    "voice_speed": "normal",
    "language": "en-US",
    "theme": "dark"
  }
}
```

### Create/Update Memory Entry
**Endpoint:** `POST /memory/entry`

**Headers:** `Authorization: Bearer <token>`

Request:
```json
{
  "key": "favorite_coffee",
  "value": "Double espresso with oat milk",
  "category": "preferences",
  "importance": 7
}
```

Response (200 OK):
```json
{
  "id": "memory-uuid",
  "key": "favorite_coffee",
  "value": "Double espresso with oat milk",
  "category": "preferences",
  "importance": 7,
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00"
}
```

**Request Parameters:**
- `key` (string, required): Memory key identifier
- `value` (string, required): Memory value/content
- `category` (string, optional, default: "general"): Memory category
- `importance` (integer, optional, default: 0): Importance scale 0-10

## Error Responses

### 400 Bad Request
```json
{
  "error": "Validation Error",
  "detail": "Invalid request format",
  "status_code": 400
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication Error",
  "detail": "Invalid or expired token",
  "status_code": 401
}
```

### 404 Not Found
```json
{
  "error": "Not Found",
  "detail": "Resource not found",
  "status_code": 404
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "detail": "An unexpected error occurred",
  "status_code": 500
}
```

## AI Providers

Supported values for `provider` parameter:
- `openai` - OpenAI GPT-4 / GPT-3.5
- `claude` - Anthropic Claude
- `gemini` - Google Gemini

Default: `openai`

## Rate Limiting

Currently disabled. Rate limiting will be implemented in Phase 2.

Suggested limits:
- Authentication endpoints: 5 requests/minute
- Chat endpoints: 30 requests/minute
- Memory endpoints: 60 requests/minute

## WebSocket Support

WebSocket support for real-time chat is planned for Phase 2.

Endpoint: `ws://localhost:8000/api/v1/ws/chat`

## Interactive API Docs

FastAPI auto-generates interactive documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

Use these to test endpoints directly in your browser.

## Pagination

Pagination will be implemented in Phase 2 for large result sets.

Current behavior returns all results (with optional `limit` parameter).

## Versioning

API version: `v1`

Future versions will be available at:
- `/api/v2`
- `/api/v3`
- etc.

Version numbers increment for breaking changes.

## Changelog

### v0.1.0 (MVP)
- ✅ Authentication (login, register)
- ✅ Health endpoint
- ✅ Basic chat endpoint
- ✅ Memory storage
- ✅ Single AI provider support

### v0.2.0 (Coming)
- 🔄 Multi-AI provider orchestration
- 🔄 Automation endpoints
- 🔄 WebSocket support
- 🔄 Rate limiting
- 🔄 Advanced pagination

### v0.3.0 (Coming)
- 🔄 File upload support
- 🔄 Image processing
- 🔄 Voice transcription
- 🔄 Scheduled tasks
- 🔄 Device integration

## Testing with Examples

### Complete Flow Example

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123",
    "name": "Test User"
  }'

# 2. Login (get token)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123"
  }' | jq -r '.access_token')

# 3. Send chat message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello Sexta-Feira!"
  }'

# 4. Get chat history
curl -X GET http://localhost:8000/api/v1/chat/history?limit=10 \
  -H "Authorization: Bearer $TOKEN"

# 5. Store memory
curl -X POST http://localhost:8000/api/v1/memory/entry \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "name",
    "value": "Test User",
    "category": "profile",
    "importance": 10
  }'

# 6. Get memory
curl -X GET http://localhost:8000/api/v1/memory \
  -H "Authorization: Bearer $TOKEN"
```

## Feedback & Improvements

For API feedback or improvement suggestions, please:
1. Create an issue in the GitHub repository
2. Describe the use case or limitation
3. Suggest an improvement or alternative design

---

For detailed architecture, see [docs/architecture.md](./architecture.md)  
For setup instructions, see [docs/setup.md](./setup.md)
