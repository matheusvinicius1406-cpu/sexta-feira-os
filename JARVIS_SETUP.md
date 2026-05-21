# 🤖 Jarvis AI System - Complete Setup & Usage Guide

## Overview

**Jarvis** is a lightweight, personal AI assistant integrated into Sexta-Feira OS. It combines:
- **FastAPI Backend** (REST API)
- **OpenJarvis-inspired Agent Framework** (Agent, Tool, Memory systems)
- **Google Gemini API** (Primary AI provider)
- **Android Mobile App** (UI)

This guide shows you how to set up and run the complete system.

---

## 🚀 Quick Start

### 1. Get Gemini API Key (5 minutes)

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account (free)
3. Click **"Create API Key"**
4. Copy the key

### 2. Configure Backend

```bash
cd /workspaces/sexta-feira-os/backend-core

# Edit .env file
nano .env

# Find this line:
# GEMINI_API_KEY=your-gemini-api-key-here

# Replace with your actual key:
# GEMINI_API_KEY=sk-...your-key...
```

### 3. Start Backend

```bash
cd /workspaces/sexta-feira-os/backend-core

# Install dependencies (if not already done)
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

✅ Backend running at: **http://localhost:8000**

### 4. Test Jarvis

In another terminal:

```bash
cd /workspaces/sexta-feira-os

# Run interactive test
python scripts/test-jarvis.py
```

---

## 📚 API Endpoints

### Health & Status

```bash
# Check backend health
curl http://localhost:8000/api/v1/health

# Get Jarvis system status
curl http://localhost:8000/api/v1/jarvis/status
```

### Authentication

```bash
# Login and get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@sextafeira.com","password":"senha12345"}'

# Response:
# {
#   "access_token": "eyJ...",
#   "token_type": "bearer",
#   "user_id": "...",
#   "expires_in": 86400
# }
```

### Jarvis Chat (Main Feature)

```bash
TOKEN="your-token-here"

curl -X POST http://localhost:8000/api/v1/jarvis/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "Hello Jarvis, what can you do?",
    "provider": "gemini"
  }'
```

### Memory System

```bash
TOKEN="your-token-here"

# Store in memory
curl -X POST http://localhost:8000/api/v1/jarvis/memory/store \
  -H "Authorization: Bearer $TOKEN" \
  -d 'key=my_preference&value=dark_mode'

# Recall from memory
curl http://localhost:8000/api/v1/jarvis/memory/recall \
  -H "Authorization: Bearer $TOKEN" \
  -d 'key=my_preference'
```

---

## 🔐 Default Test User

- **Email**: teste@sextafeira.com
- **Password**: senha12345

You can register new users via `/api/v1/auth/register` endpoint.

---

## 📖 Interactive API Documentation

Once backend is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Explore all endpoints, see parameters, and test directly in the browser!

---

## 🏗️ System Architecture

```
Sexta-Feira OS
├── Backend (FastAPI)
│   ├── Authentication (JWT)
│   ├── Chat API
│   ├── Memory System
│   ├── Jarvis System
│   │   ├── Agent Framework
│   │   ├── Tool Registry
│   │   └── Memory Management
│   └── Database (SQLite/PostgreSQL)
├── Jarvis AI (Gemini Provider)
│   ├── GeminiProvider (low-level API)
│   ├── GeminiOrchestratorV2 (high-level chat)
│   └── Context Management
└── Android App (Kotlin)
    ├── Login Screen
    ├── Chat Screen
    ├── Dashboard
    ├── Settings
    └── Network Layer
```

---

## 📝 Configuration Files

### `.env` - Environment Variables

```env
# Backend Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Database
DATABASE_URL=sqlite:///./data/sexta_feira_os.db

# JWT Authentication
JWT_SECRET_KEY=dev-sexta-feira-os-super-secret-key-change-in-production-2024
JWT_EXPIRATION_HOURS=24

# Gemini AI (REQUIRED FOR PRODUCTION)
GEMINI_API_KEY=your-gemini-api-key-here
DEFAULT_AI_PROVIDER=gemini

# Jarvis System
JARVIS_SYSTEM_NAME=Jarvis
JARVIS_ENABLE_MEMORY=true
JARVIS_ENABLE_LEARNING=true
JARVIS_ENABLE_TOOLS=true
JARVIS_TEMPERATURE=0.7
JARVIS_MAX_TOKENS=2000
```

---

## 🔧 Troubleshooting

### 1. `ModuleNotFoundError: No module named 'google.generativeai'`

```bash
cd backend-core
pip install -r requirements.txt
```

### 2. `GEMINI_API_KEY environment variable not set`

System works with mock responses, but to use real Gemini:

```bash
# In .env:
GEMINI_API_KEY=sk-your-real-key-here

# OR set environment variable:
export GEMINI_API_KEY=sk-your-real-key-here
uvicorn app.main:app --reload
```

### 3. `Port 8000 already in use`

```bash
# Find process using port 8000
lsof -i :8000

# Kill it (replace PID):
kill -9 <PID>

# Or use different port:
uvicorn app.main:app --port 8001
```

### 4. `Database locked` or `no such table`

```bash
# Reinitialize database:
cd backend-core
rm -f data/sexta_feira_os.db
python init_db.py
```

---

## 📱 Android App Integration

### Update API Endpoint (WIP)

File: `mobile-android/app/src/main/kotlin/com/sextafeira/os/data/api/SextaFeiraApi.kt`

```kotlin
companion object {
    // For emulator (backend running on host)
    const val API_BASE_URL = "http://10.0.2.2:8000/"
    
    // For device (backend running on real server)
    // const val API_BASE_URL = "https://your-server.com/"
}
```

### Connect to Backend

The Android app will connect to:
- `/api/v1/auth/login` - Authentication
- `/api/v1/jarvis/chat` - Chat with Jarvis
- `/api/v1/jarvis/status` - System status
- `/api/v1/memory/*` - Memory operations

---

## 🎯 Example: Full Conversation Flow

### 1. Register New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123",
    "name": "John Doe"
  }'
```

### 2. Login

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}' | jq -r .access_token)

echo $TOKEN  # See your token
```

### 3. Store Memory

```bash
curl -X POST http://localhost:8000/api/v1/jarvis/memory/store \
  -H "Authorization: Bearer $TOKEN" \
  -d 'key=favorite_color&value=blue'
```

### 4. Chat with Jarvis

```bash
curl -X POST http://localhost:8000/api/v1/jarvis/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "What is my favorite color?"
  }'

# Response will include:
# "I remember your favorite color is blue."
```

---

## 🚀 Next Steps

1. ✅ Get Gemini API key
2. ✅ Configure `.env`
3. ✅ Start backend
4. ✅ Test with curl
5. 🔜 Connect Android app
6. 🔜 Build AI tools framework
7. 🔜 Implement learning system
8. 🔜 Deploy to production

---

## 📞 Support

### Documentation Files
- [API Documentation](../docs/api.md)
- [Architecture Overview](../docs/architecture.md)
- [Setup Guide](../docs/setup.md)

### Key Project Files

Backend:
- `backend-core/app/main.py` - FastAPI application
- `backend-core/app/jarvis/` - Jarvis AI system
- `backend-core/app/ai/orchestrator.py` - AI provider routing
- `backend-core/app/api/routers/jarvis.py` - Jarvis endpoints

Android:
- `mobile-android/app/src/main/kotlin/com/sextafeira/os/MainActivity.kt` - Main activity
- `mobile-android/app/src/main/kotlin/com/sextafeira/os/ui/screens/` - UI screens
- `mobile-android/app/src/main/kotlin/com/sextafeira/os/data/api/` - Network layer

---

## 🎓 Learn More

- **FastAPI**: https://fastapi.tiangolo.com
- **Google Gemini**: https://makersuite.google.com
- **Jetpack Compose**: https://developer.android.com/jetpack/compose
- **SQLAlchemy**: https://www.sqlalchemy.org

---

**Made with 💜 for Sexta-Feira OS**
