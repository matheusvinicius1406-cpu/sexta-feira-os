# Current Priorities

## 1. Define the MVP scope

- Finalize the core use cases for the first Android voice assistant release.
- Identify 3–5 initial automation flows (reminders, notes, quick actions).
- Confirm the backend data model for user memory and interaction history.

## 2. Establish the backend foundation

- Create FastAPI service skeleton in `/backend-core`.
- Add persistent storage support with SQLite and PostgreSQL compatibility.
- Implement a memory store interface for long-term context and session recall.

## 3. Build the Android shell

- Create the Android project structure in `/mobile-android` with Kotlin and Jetpack conventions.
- Build a voice capture screen and a response display component.
- Set up network service layer for backend API calls.

## 4. Design the integration layer

- Define adapter interfaces for multi-AI provider integration.
- Create an orchestration module that decides which AI service or automation agent handles a request.
- Document integration expectations in `/docs`.

## 5. Set up documentation and governance

- Keep `/docs` updated with architecture decisions, user journeys, and API contracts.
- Keep `PROJECT_CONTEXT.md`, `ROADMAP.md`, and `TASKS.md` current with each sprint.

## 6. Prepare for future expansion

- Reserve architecture and file structure for smart glass support.
- Design memory abstractions that can be extended with vision and sensor context.
- Identify the first wearable-related research tasks.
