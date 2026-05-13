# Setup Guide

## Prerequisites

### Required
- Python 3.10+
- Android SDK + Android Studio
- Git
- Docker & Docker Compose (recommended)

### Optional
- PostgreSQL client tools
- Postman or Insomnia (API testing)
- Redis CLI

## Backend Setup

### Local Development (No Docker)

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/matheusvinicius1406-cpu/sexta-feira-os.git
   cd sexta-feira-os/backend-core
   ```

2. **Create Python virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp ../.env.example ../.env
   # Edit .env with your configuration
   nano ../.env
   ```

5. **Create database tables:**
   ```bash
   python -c "from app.db.database import Base, engine; Base.metadata.create_all(bind=engine)"
   ```

6. **Run the server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   Backend available at: `http://localhost:8000`
   API Docs: `http://localhost:8000/docs`

### Docker Compose Setup

1. **From project root:**
   ```bash
   docker-compose up -d
   ```

2. **Verify services:**
   ```bash
   docker-compose ps
   ```

3. **Access services:**
   - Backend API: `http://localhost:8000`
   - PostgreSQL: `localhost:5432`
   - Redis: `localhost:6379`

4. **Stop services:**
   ```bash
   docker-compose down
   ```

## Android Setup

### Prerequisites
- Android Studio Flamingo or later
- Android SDK 24+ (Min SDK)
- JDK 17+

### Setup Steps

1. **Open project in Android Studio:**
   ```bash
   cd mobile-android
   # Open in Android Studio
   ```

2. **Sync Gradle files:**
   - Android Studio will automatically prompt to sync
   - Wait for indexing to complete

3. **Create Android Virtual Device (AVD):**
   - Device Manager → Create Device
   - Select API 34 (latest)
   - Configure and launch

4. **Run the app:**
   ```bash
   ./gradlew assembleDebug  # Build APK
   ./gradlew installDebug   # Install on device/emulator
   ```

   Or use Android Studio's Run button

### Building Production APK

```bash
./gradlew assembleRelease  # Requires signing config
```

## Environment Configuration

### Create `.env` file:

```bash
cp .env.example .env
```

### Edit configuration:

```bash
# Backend Service
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sexta_feira_os
SQLITE_DB_PATH=./data/sexta_feira_os.db

# JWT
JWT_SECRET_KEY=your-secure-random-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# AI Providers
OPENAI_API_KEY=sk-your-openai-key
CLAUDE_API_KEY=your-claude-key
GEMINI_API_KEY=your-gemini-key
DEFAULT_AI_PROVIDER=openai

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Logging
LOG_LEVEL=INFO
```

## Testing the API

### Using Curl

```bash
# Health check
curl http://localhost:8000/api/v1/health

# User registration
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123", "name": "John Doe"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123"}'

# Send chat message (use token from login)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "provider": "openai"}'
```

### Using Insomnia/Postman

Import the API collection from `/docs` (TODO: export collection)

## Database Management

### SQLite (Development)
```bash
sqlite3 sexta_feira_os.db
SQLite> .tables
SQLite> SELECT * FROM users;
```

### PostgreSQL (Production)
```bash
psql -U user -d sexta_feira_os -c "SELECT * FROM users;"
```

### Reset Database
```bash
# Remove data
rm sexta_feira_os.db

# Restart backend to recreate tables
```

## Common Issues

### Port Already in Use
```bash
# Kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app.main:app --port 8001
```

### Database Connection Error
```bash
# Check DATABASE_URL in .env
# Ensure PostgreSQL is running (if using Postgres)
# Fallback to SQLite by changing DATABASE_URL
```

### Android Build Failure
```bash
# Clean and rebuild
./gradlew clean
./gradlew build

# Clear Android Studio cache
File → Invalidate Caches
```

### Missing Dependencies
```bash
# Backend
pip install --upgrade pip
pip install -r requirements.txt

# Android
Tools → SDK Manager → Install missing SDKs
```

## Development Workflow

### Backend Development
```bash
# Terminal 1: Run server with auto-reload
uvicorn app.main:app --reload

# Terminal 2: Run tests
pytest tests/

# Terminal 3: Code formatting
black app/
```

### Android Development
```bash
# Run with logs
./gradlew run --info

# Run tests
./gradlew test

# Format code
./gradlew spotlessApply
```

## Production Deployment

### Backend Deployment (Docker)
```bash
# Build image
docker build -t sexta-feira-backend:latest backend-core/

# Run container
docker run -p 8000:8000 \
  --env-file .env \
  sexta-feira-backend:latest
```

### Android Deployment
```bash
# Sign APK
./gradlew bundleRelease

# Upload to Google Play Console
# (Follow Google Play guidelines)
```

## Next Steps

1. Configure AI provider API keys in `.env`
2. Test health endpoint: `GET /api/v1/health`
3. Create test user account
4. Explore `/docs` (Swagger UI) for full API
5. Review `docs/architecture.md` for system design

## Support & Troubleshooting

- Check logs in backend terminal
- Enable debug mode: `DEBUG=true` in .env
- Review FastAPI error responses in browser
- Check Android Logcat for mobile issues

For detailed architecture, see [docs/architecture.md](./architecture.md)
