# OntDekker — Parallel Development & Integration Guidelines

This document details the team organization, service boundaries, git workflows, and integration standards for the OntDekker platform engineering team.

---

## 👥 Ownership Matrix
- **Developer 1 (IAM & Identity):** Owns `authentication-service` and `user-service`. Responsible for shared packages and security helpers.
- **Developer 2 (Social & Content):** Owns `feed-service` and `community-service`. Responsible for Traefik API Gateway configurations and REST API routing rules.
- **Developer 3 (Expeditions & Guides):** Owns `expedition-service` and `guide-service`. Responsible for Postgres migrations, MinIO setup, Redis configurations, and local Compose networks.
- **Shared Responsibility:** `recommendation-service`, `chat-service`, `notification-service`, `moderation-service`, CI/CD pipelines, and platform monitoring.

---

## 🚪 Service & Dependency Boundaries

To prevent tight coupling and service blockages, developers must adhere to the following rules:

### 1. Database per Service
- Each microservice owns exactly **one** database.
- Direct cross-service database access is prohibited. All data sharing occurs via REST APIs or Kafka events.
- Database migrations must be managed locally within each service using Alembic.

### 2. No Cross-Domain Database Joins or Constraints
- Store reference keys as raw UUID fields. Do not declare database-level Foreign Keys pointing to tables in other microservices.
- Example: `feed-service` stores `author_id: UUID` (referencing `user-service`), but no foreign key exists in the database. Referential integrity is validated at the application level.

### 3. Service Separation
- No direct code imports between services. Each service compiles to a separate image.
- Shared code belongs strictly in the `shared/` package. The `shared/` package must remain thin and free of business logic.

---

## 🔄 Integration Guidelines

### 1. Synchronous REST APIs
- All public endpoints must utilize the gateway prefix standard: `/api/v1/{service-name}/*`.
- Traefik strips the prefix before forwarding to the microservice port.
- Standard error structures must be returned using the `shared.exceptions` utilities.

### 2. Real-Time WebSockets
- WebSocket connections are isolated to `chat-service`.
- WebSockets must require JWT validation during handshake. Connections fail with `4401` on token expiration.
- Connection replication across scaling instances is coordinated via Redis Pub/Sub.

### 3. Asynchronous Events (Kafka)
- **Database-First, Event-Second:** Events must be published *after* database transactions commit successfully. Never publish events for uncommitted database changes.
- **Idempotency:** Consumers must track processed message IDs (`event_id` UUID) and discard duplicates to survive network redeliveries safely.
- **Event Versioning:** All event schemas inside `shared/events/models.py` include an `event_version` parameter. Payload alterations must be backward compatible.

---

## 🌿 Git Workflow & PR Policies

1. **Rebase-First Policy:** Developers must rebase their feature branch on top of `develop` before submitting a Pull Request (`git pull --rebase origin develop`).
2. **Pull Request Scope:** A PR must only focus on one microservice or a specific shared feature. Do not bundle authentication changes with feed updates.
3. **PR Review Checklist:**
   - [ ] All unit and integration tests pass.
   - [ ] Code complies with PEP 8 (`black`, `ruff`, `isort`).
   - [ ] Database migrations are generated via Alembic.
   - [ ] Environment variables are added to `.env.example`.
   - [ ] OpenAPI documentation is verified.
4. **Definition of Done (DoD):**
   - Business logic complete and fully typed.
   - Unit tests cover all success/failure cases.
   - Docker image builds successfully.
   - JSON logs include request and correlation tracking.
   - Code is approved by at least one other developer.
   - Merged into `develop` and verified through integration runs.
