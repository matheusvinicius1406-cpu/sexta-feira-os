# 90-Day Launch Roadmap

## Goal
Launch a functional MVP of Sexta-Feira OS with a native Android voice assistant, backend memory persistence, and initial automation capabilities.

## Phase 1: Foundation & architecture (Weeks 1-4)

- Define core user stories and success metrics
- Establish API contracts for voice, memory, and automation
- Build the backend skeleton with FastAPI, auth conventions, and local persistence support
- Create Android app scaffold with voice command entry, core navigation, and baseline UI patterns
- Document architecture, data model, and integration strategy in `/docs`

### Key deliverables
- `backend-core` service skeleton
- `mobile-android` app scaffold with basic voice entry point
- `PROJECT_CONTEXT.md`, `ROADMAP.md`, `TASKS.md` completed
- Initial tech spike for multi-AI integration approach

## Phase 2: MVP implementation (Weeks 5-8)

- Implement persistent memory store for user context and session history
- Enable voice assistant workflow: capture voice input -> backend intent handling -> response rendering
- Add first AI integration stub and a simple orchestration handler
- Build automation primitives for reminders, task scheduling, and quick actions
- Validate end-to-end mobile backend connectivity with sample flows

### Key deliverables
- Persistent memory API in backend
- Voice assistant end-to-end MVP on Android
- Basic automation engine with one or two task types
- Prototype integration with a single AI provider or local model API

## Phase 3: Polish, validation & launch readiness (Weeks 9-12)

- Refine voice UX and error handling in the Android client
- Harden backend stability, logging, and testing coverage
- Add offline-safe startup behavior using SQLite fallbacks
- Create onboarding and setup flows for first-time users
- Conduct internal usability reviews and iterate on priority improvements
- Prepare launch documentation, architecture notes, and product brief

### Key deliverables
- Stable MVP release candidate
- Internal validation checklist and bug backlog
- Launch plan including initial user feedback loop
- `docs` repository with design rationale and next-phase proposals

## Milestones

- Week 4: Architecture complete, MVP scope finalized
- Week 8: End-to-end assistant flow working with persistent context
- Week 12: Launch-ready MVP and documented path to smart glasses integration

## Risks and mitigations

- AI integration complexity: start with a single provider and abstract the adapter layer.
- Voice UX friction: iterate quickly with real user flows and fallback text inputs.
- Data persistence consistency: use SQLite locally and PostgreSQL for backend session storage.
