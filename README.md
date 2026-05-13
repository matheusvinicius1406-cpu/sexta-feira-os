# Sexta-Feira OS 🎯

**A production-ready AI personal assistant platform for the discerning user.**

Sexta-Feira OS is an elite-level personal AI assistant inspired by JARVIS and FRIDAY. It delivers a native Android experience with voice-first interaction, persistent contextual memory, intelligent automation, and multi-AI orchestration. Built for a single owner who demands privacy, control, and sophistication.

## Vision

Create a personal digital brain that anticipates intent, remembers context, automates routines, and evolves with the user—across mobile devices, cloud infrastructure, and future wearable experiences.

## Key Differentiators

✨ **Voice-First & Natural** — Expressive voice commands and intelligent responses powered by multiple AI providers  
💾 **Persistent Memory** — Long-term context retention, habit tracking, and personalized intelligence  
🚀 **Modular Architecture** — Clean layered design supporting rapid iteration and AI provider swaps  
⚙️ **Automation Engine** — Intelligent task scheduling, trigger-based workflows, and device orchestration  
🔒 **Private & Secure** — JWT authentication, local fallbacks, and future-proof encryption  
👓 **Future-Ready** — Designed for seamless expansion into smart glasses and edge computing  

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Mobile** | Kotlin + Jetpack Compose + Material 3 | Native Android UI with modern patterns |
| **Backend** | Python + FastAPI | High-performance async REST API |
| **Database** | PostgreSQL + SQLite | Production-grade + local fallbacks |
| **Authentication** | JWT + OAuth2-ready | Secure session and token management |
| **AI Orchestration** | Modular adapters | OpenAI, Claude, Gemini, local models |
| **DevOps** | Docker + Docker Compose | Containerized, reproducible deployments |

## Project Structure

```
sexta-feira-os/
├── mobile-android/          # Kotlin Android app (Compose, MVVM)
│   ├── app/                 # Main app module
│   ├── core/                # Shared utilities & infrastructure
│   └── build.gradle.kts     # Gradle configuration
├── backend-core/            # FastAPI backend service
│   ├── app/                 # Application layers
│   │   ├── api/             # REST endpoint routers
│   │   ├── core/            # Config & dependencies
│   │   ├── models/          # Database ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic
│   │   ├── memory/          # Memory & context management
│   │   ├── ai/              # AI provider orchestration
│   │   └── auth/            # Authentication & authorization
│   ├── main.py              # FastAPI entry point
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile           # Docker image definition
├── docs/                    # Architecture & design documentation
├── scripts/                 # Utility scripts & deployment tools
├── shared/                  # Shared models, constants across services
├── docker-compose.yml       # Local development environment
├── .env.example             # Environment configuration template
└── README.md               # This file
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js / Android SDK (for mobile)
- Docker & Docker Compose (recommended)

### Run Backend Locally

```bash
cd backend-core
pip install -r requirements.txt
cp ../.env.example ../.env
# Edit .env with your API keys
python -m uvicorn app.main:app --reload
# Backend available at http://localhost:8000
```

### Run with Docker Compose

```bash
docker-compose up -d
# PostgreSQL: localhost:5432
# Backend: http://localhost:8000
# Redis: localhost:6379
```

### Android Development

```bash
cd mobile-android
# Open in Android Studio or build with Gradle
./gradlew assembleDebug
```

## Documentation

- **[PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)** — Mission, principles, long-term vision
- **[ROADMAP.md](./ROADMAP.md)** — 90-day MVP launch plan with milestones
- **[TASKS.md](./TASKS.md)** — Current actionable priorities
- **[docs/architecture.md](./docs/architecture.md)** — System design & integration patterns
- **[docs/setup.md](./docs/setup.md)** — Detailed environment setup guide
- **[docs/api.md](./docs/api.md)** — REST API endpoint documentation

## Development Status

✅ **Foundation Phase** — Production-grade project structure, Docker setup, and development scaffolds ready.  
🔄 **MVP Phase** — Core Android screens, backend authentication, memory store, and basic AI integration in progress.  
📋 **Coming Soon** — Voice input pipeline, automation engine, multi-provider orchestration.

## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update with your configuration:
   - Database credentials
   - AI provider API keys
   - JWT secret (generate a random one)
   - CORS origins for development

3. For Docker: `docker-compose up -d`

## Architecture Principles

- **Clean Architecture** — Separation of concerns via layered modules
- **DRY (Don't Repeat Yourself)** — Shared utilities in `/shared` and `/core`
- **SOLID Principles** — Dependency injection, interface-based design
- **Async-First** — FastAPI async patterns for high concurrency
- **Provider Abstraction** — Swap AI providers without core changes

## Contributing

This project follows startup-grade engineering standards:

- Clear commit messages describing the "why"
- Feature branches for all work (`feature/feature-name`)
- Code review before merge to `main`
- Documentation updates alongside code changes
- Keep `/docs` current with architectural decisions

## License

MIT License — See [LICENSE](./LICENSE) file for details.

---

**Built with ❤️ for an AI-powered future.**

*For detailed setup instructions, see [docs/setup.md](./docs/setup.md)*  
*For architecture deep-dives, see [docs/architecture.md](./docs/architecture.md)*
