# OntDekker — Complete Project Handover Document

**Version:** 3.0
**Date:** 2026-07-25
**Author:** Kiro AI (Senior Engineer / Pair Programmer)
**Purpose:** Complete handover for continuing OntDekker implementation in a new chat session. Zero memory assumed.

---

## 1. PROJECT OVERVIEW

### Vision

OntDekker (Dutch: "Discoverer") is a premium slow-travel community platform. It is a production-grade microservices monorepo built with Python/FastAPI backends, a Next.js frontend, and PostgreSQL-per-service databases. The platform connects mindful travelers with verified local guides and community-driven expedition planning.

### Product Goals

- Replace rushed tourism with immersive, community-led travel experiences
- Build a trusted network between slow travelers, local guides, and expedition planners
- Provide authentic travel content discovery (not algorithmic noise)
- Enable collaborative trip planning with gear optimization

### Features

1. **Discover Feed** — Travel story cards with rich media, social interactions (likes, bookmarks, shares), comments, tags, and chronological timeline
2. **Communities** — Location-based groups with public/private visibility, membership management, join requests, moderation tools, community rules, and discussion forums
3. **Expedition Workspace** — Collaborative trip planning with participants, itineraries, shared galleries, and gear weight optimizer
4. **Verified Guide Directory** — Professional profiles, specialties, availability, ratings, and relationship tracking
5. **Real-time Chat** — Private, community, and expedition messaging with presence indicators (Phase 2)
6. **Pack Weight Optimizer** — Gear recommendation engine for ultralight/lightweight/traditional travel styles
7. **Async Notifications** — Event-driven updates across all platform activities (Phase 2)

### Explicitly Excluded Features

- NOT a booking platform — no hotel/flight reservations or payment processing
- NOT a marketplace — no direct monetary transactions or escrow
- NOT a navigation app — no GPS routing or offline maps
- NOT AI-generated content — human-only stories and recommendations
- NO payment processing — all monetary transactions happen outside the platform

### Architecture Philosophy

- **Microservices** — one service per business domain, strict boundaries
- **Database-per-Service** — each service owns its PostgreSQL database completely; no cross-service DB access ever
- **Clean Architecture** — Presentation → Service → Repository → Infrastructure in every service
- **Event-driven (Phase 2)** — Kafka for async communication; REST for synchronous in Phase 1
- **API-first** — frontend consumes REST APIs only; never touches databases directly
- **SOLID Principles** — dependency injection, single responsibility throughout
- **No cross-service database queries** — services communicate via APIs or Kafka events only

### Development Approach

- Backend-first: complete backend per checkpoint before touching frontend
- Feed Service is the canonical reference implementation — every other service follows identical patterns
- Checkpoint-driven: discrete, deliverable-based milestones
- Parallel ownership: three developers with non-overlapping service boundaries

---

## 2. TECHNOLOGY STACK

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.12 spec / 3.13.5 local | Primary backend language |
| Framework | FastAPI async | >=0.110.0 | REST API with automatic OpenAPI docs |
| ORM | SQLAlchemy 2.0 async | >=2.0.0 | Database modeling and async queries |
| Migrations | Alembic | >=1.13.0 | Database schema versioning |
| Validation | Pydantic v2 | >=2.6.0 | Request/response validation |
| Settings | pydantic-settings | >=2.2.0 | Environment-based configuration |
| Auth | python-jose[cryptography] | >=3.3.0 | JWT tokens |
| Passwords | passlib[bcrypt] + bcrypt | >=1.7.4 / >=4.1.0 | Password hashing |
| HTTP Server | Uvicorn | >=0.28.0 | ASGI server for FastAPI |
| DB Driver | asyncpg | >=0.29.0 | Async PostgreSQL driver |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Next.js | React-based full-stack framework |
| UI | React + TypeScript | Component-based UI with type safety |
| Styling | Tailwind CSS | Utility-first CSS |
| Components | shadcn/ui | Pre-built accessible components |
| State | AppStateProvider React Context | Global application state |
| Data Fetching | TanStack Query + Axios | Server state management and HTTP client |
| Routing | State-driven virtual router SPA | Custom single-page application routing |

### Databases

| Service | Database | Technology |
|---------|----------|-----------|
| authentication-service | auth_db | PostgreSQL 16 |
| user-service | user_db | PostgreSQL 16 |
| feed-service | feed_db | PostgreSQL 16 |
| community-service | community_db | PostgreSQL 16 |
| expedition-service | trip_db | PostgreSQL 16 |
| guide-service | guide_db | PostgreSQL 16 |
| recommendation-service | recommendation_db | PostgreSQL 16 |
| chat-service | chat_db | PostgreSQL 16 |
| notification-service | notification_db | PostgreSQL 16 |
| moderation-service | moderation_db | PostgreSQL 16 |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Gateway | Traefik v2.10 | Load balancing, SSL termination, routing |
| Object Storage | MinIO | S3-compatible media storage |
| Cache | Redis 7 | Session storage, caching layer |
| Event Streaming | Apache Kafka KRaft | Async message streaming Phase 2 |
| Containers | Docker + Docker Compose | Service containerization |
| Monitoring | Prometheus + Grafana + Loki | Metrics, dashboards, log aggregation |

### Kafka

- Current status: dependencies installed but not configured in any service
- Phase 2 implementation: event streaming for notifications, recommendations, moderation
- Shared models exist: `shared/events/models.py` contains Kafka event schemas
- Topics defined: `shared/constants/topics.py` contains `KafkaTopic` enum
- Phase 1: Kafka is NOT used. All communication is synchronous REST.

### Redis

- Current status: listed in docker-compose.yml infrastructure but not integrated into any service
- Planned use: session storage, caching for JWT validation, rate limiting
- Phase 1: Redis is NOT integrated into any service yet

### MinIO

- Purpose: S3-compatible object storage for all binary media (images, future video)
- Buckets planned: `posts` (feed-service), `communities` (community-service)
- Integration pattern: service generates presigned URL → client uploads directly to MinIO → client sends `object_key` back to service → service stores URL in PostgreSQL, never the binary data
- Current status: MinIO container exists in docker-compose.yml. Presigned URL generation in feed-service is stubbed (returns a placeholder URL). Community service MinIO not yet implemented.

### Traefik

- Purpose: API gateway routing all `/api/v1/*` traffic to correct services
- Current status: README stubs only. No actual Traefik config files exist.
- Planned routes:
  - `/api/v1/auth/*` → authentication-service:8000
  - `/api/v1/users/*` → user-service:8000
  - `/api/v1/feed/*` → feed-service:8000
  - `/api/v1/communities/*` → community-service:8000
  - `/api/v1/expeditions/*` → expedition-service:8000
  - `/api/v1/guides/*` → guide-service:8000

### Docker

- All 10 services have Dockerfiles (basic, functional)
- `docker-compose.yml` at root is INCOMPLETE — only contains infrastructure services (PostgreSQL, Redis, MinIO, Kafka stubs). Application service entries are missing.
- `make run` is the only Makefile target

### Testing

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | pytest | Primary testing framework |
| Async Testing | pytest-asyncio | Async test support |
| Code Quality | black, ruff, isort, mypy | Formatting, linting, type checking |

### Shared Package

The `shared/` directory is a Python package installed by all services. It provides:

- `shared.database` — Base, TimestampMixin, SoftDeleteMixin, AuditMixin
- `shared.config` — CommonSettings (JWT, Kafka, Redis base config)
- `shared.dependencies` — FastAPI dependencies: get_db, get_request_id, get_current_user, optional_current_user, require_role
- `shared.exceptions` — full exception hierarchy + short-form aliases (see section 12)
- `shared.logging` — structured logging with setup_logging, context vars
- `shared.events.models` — Kafka event schemas
- `shared.constants.status` — all status/visibility/role enums
- `shared.constants.roles` — UserRole enum
- `shared.constants.topics` — KafkaTopic enum
- `shared.schemas.responses` — standard response wrappers
- `shared.utils.security` — JWT encode/decode helpers
- `shared.utils.generators` — UUID generators
- `shared.utils.retry` — retry decorators
- `shared.utils.date_helpers` — date/time utilities

---

## 3. REPOSITORY STRUCTURE

### Location

```
Local path:  /Users/prajwalnaganagoudar/Desktop/OntDekkers/
Remote:      https://github.com/VishnuChitturi/OntDekkers.git
```

### Top-Level Layout

```
OntDekkers/
├── apps/
│   └── web/                    # Next.js frontend — SKELETON ONLY
├── services/
│   ├── authentication-service/ # Dev 1 — SKELETON
│   ├── user-service/           # Dev 1 — SKELETON
│   ├── feed-service/           # Dev 2 — FULLY IMPLEMENTED
│   ├── community-service/      # Dev 2 — IN PROGRESS (task 4/9)
│   ├── expedition-service/     # Dev 3 — SKELETON
│   ├── guide-service/          # Dev 3 — SKELETON
│   ├── recommendation-service/ # Phase 2 — SKELETON
│   ├── chat-service/           # Phase 2 — SKELETON
│   ├── notification-service/   # Phase 2 — SKELETON
│   └── moderation-service/     # Phase 2/3 — SKELETON
├── shared/                     # Shared Python package — PARTIALLY IMPLEMENTED
├── platform/                   # Gateway + observability — README stubs only
├── infrastructure/             # Docker configs — README stubs only
├── Docs/                       # ALL DOCUMENTATION — FULLY WRITTEN (75KB+)
├── docker-compose.yml          # INCOMPLETE — infrastructure only
├── Makefile                    # Minimal — only make run
├── .env.example                # Only ENVIRONMENT=development
└── .github/workflows/ci.yml    # Empty stub
```

### Standard Service Structure

Every microservice follows this identical structure:

```
{service-name}/
├── app/
│   ├── __init__.py
│   ├── api/                    # REST API routers
│   ├── config/                 # Pydantic settings
│   ├── core/                   # FastAPI app factory + health check
│   ├── database/               # Async SQLAlchemy engine + session
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── repositories/           # Data access layer
│   ├── services/               # Business logic layer
│   ├── dependencies/           # FastAPI dependency overrides
│   ├── events/                 # Kafka event models Phase 2
│   ├── workers/                # Background tasks future
│   └── middleware/             # Custom middleware future
├── alembic/
│   ├── __init__.py
│   ├── env.py
│   └── versions/
├── tests/
│   ├── __init__.py
│   └── conftest.py
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── README.md
└── .env.example
```

### Feed Service — Files Confirmed Present

```
app/models/post.py                   Post, PostMedia, PostTag
app/models/interaction.py            Like, Bookmark, Share
app/models/comment.py                Comment (one-level nesting)
app/models/__init__.py               exports all models
app/schemas/feed.py                  all request/response schemas
app/schemas/__init__.py
app/repositories/post_repository.py  async CRUD + filtering (15KB)
app/repositories/interaction_repository.py
app/repositories/comment_repository.py
app/repositories/__init__.py
app/services/post_service.py         full business logic (17KB)
app/services/comment_service.py
app/services/media_service.py        MinIO presigned URL stubbed
app/services/__init__.py
app/api/posts.py
app/api/interactions.py
app/api/comments.py
app/api/media.py
app/api/routes.py                    combines all routers
app/api/__init__.py
app/core/main.py                     FastAPI app with lifespan + health check
app/config/settings.py
app/database/engine.py
app/database/session.py
alembic/env.py                       imports all models, async migrations
alembic/versions/001_initial.py      complete migration for feed_db
requirements.txt
```

### Community Service — Files Confirmed Present

```
app/models/community.py              Community model  DONE
app/models/membership.py             CommunityMember, JoinRequest  DONE
app/models/rule.py                   CommunityRule  DONE
app/models/discussion.py             Discussion, DiscussionComment  DONE
app/models/__init__.py               exports all 6 models  DONE
app/schemas/community.py             all request/response schemas  DONE
app/schemas/__init__.py              exports all schemas  DONE
app/repositories/                    EMPTY — task 4 interrupted
app/services/                        EMPTY
app/api/                             EMPTY
app/core/main.py                     skeleton FastAPI app, no routes wired
app/config/settings.py               community-service settings
alembic/env.py                       skeleton, models not imported yet
alembic/versions/                    EMPTY — no migration created
requirements.txt                     basic deps only
```

### Shared Library — Files Confirmed Present

```
shared/__init__.py                   exports all symbols including aliases
shared/database.py                   Base, TimestampMixin, AuditMixin, SoftDeleteMixin
shared/exceptions.py                 full hierarchy + NotFoundError/ForbiddenError/ValidationError/ConflictError/UnauthorizedError aliases
shared/dependencies.py               get_db, get_current_user, optional_current_user, require_role
shared/config.py                     CommonSettings
shared/logging.py                    structured logging
shared/constants/status.py           ALL enums
shared/events/models.py              Kafka schemas stub
shared/utils/security.py             JWT helpers
```

### What Is Completely Missing

- Frontend: `apps/web/src/` — completely empty, no implementation
- Traefik configuration files
- docker-compose.yml entries for application services
- MinIO bucket initialization scripts
- Database initialization scripts (CREATE DATABASE statements)
- GitHub Actions CI/CD pipeline implementation
- Any test implementations (conftest.py files are empty stubs)

---

## 4. MICROSERVICE ARCHITECTURE

### Authentication Service

- Owner: Developer 1
- Responsibility: Identity and access management. User registration, login, JWT generation/validation, refresh tokens, email verification, password reset, role management.
- Database: auth_db
- Status: SKELETON — basic FastAPI app only
- Key rule: ONLY service that GENERATES JWTs. All other services only VALIDATE tokens.
- Dependencies: None (foundational service)

### User Service

- Owner: Developer 1
- Responsibility: User profiles, travel preferences, social connections, reputation system, badges, saved content references. Does NOT handle authentication credentials.
- Database: user_db
- Status: SKELETON — basic FastAPI app only
- Key rule: Stores `auth_user_id` as a plain UUID reference, never passwords or auth tokens.
- Dependencies: Authentication Service (JWT validation)

### Feed Service — FULLY IMPLEMENTED

- Owner: Developer 2
- Responsibility: Travel post lifecycle (create/edit/delete with soft delete), media references (MinIO URLs), social interactions (likes, bookmarks, shares), nested comments (one level of replies), chronological feed retrieval with filtering/pagination/search, authorization and visibility controls.
- Database: feed_db
- Tables: posts, post_media, post_tags, likes, bookmarks, shares, comments
- Status: COMPLETE — full models, repositories, services, API endpoints, Alembic migration
- Dependencies: Authentication (JWT), User Service (future enrichment), MinIO (media), Kafka (Phase 2)
- NOT responsible for: user profiles, community lifecycle, feed ranking, push notifications, content moderation

### Community Service — IN PROGRESS

- Owner: Developer 2
- Responsibility: Community lifecycle (create, edit, archive, delete), membership management (join requests, approval, role management), community rules, discussion forums with comments, community media (logos, banners).
- Database: community_db
- Tables: communities, community_members, join_requests, community_rules, discussions, discussion_comments
- Status: Models DONE, Schemas DONE, Repositories EMPTY, Services EMPTY, API EMPTY, Migration EMPTY
- Dependencies: Authentication (JWT), User Service (member info), MinIO (logos/banners), Kafka (Phase 2)

### Expedition Service

- Owner: Developer 3
- Responsibility: Expedition lifecycle (planning, active, completed), participant management, collaborative itinerary building, shared photo galleries, gear planner with weight optimization, post-trip reviews and ratings.
- Database: trip_db
- Status: SKELETON

### Guide Service

- Owner: Developer 3
- Responsibility: Guide application and verification, professional profiles, specialties, language capabilities, geographic coverage areas, availability calendars, rating/review system, traveler-guide relationship tracking.
- Database: guide_db
- Status: SKELETON

### Recommendation Service

- Owner: Shared Phase 2
- Responsibility: Personalized feed ranking, content recommendations, trending content identification. Does NOT own any content.
- Database: recommendation_db
- Status: SKELETON
- Key rule: Only produces ranked lists of content IDs — never stores actual content.

### Chat Service

- Owner: Shared Phase 2
- Responsibility: Real-time messaging via WebSockets. Message persistence, read receipts, typing indicators, presence.
- Database: chat_db
- Status: SKELETON

### Notification Service

- Owner: Shared Phase 2
- Responsibility: Async in-app notification delivery driven by Kafka events. Preference management, grouping/batching, read/unread state.
- Database: notification_db
- Status: SKELETON

### Moderation Service

- Owner: Shared Phase 2/3
- Responsibility: Content reporting, moderator action tracking (warnings, suspensions, bans), audit logs, appeal process.
- Database: moderation_db
- Status: SKELETON

---

## 5. TEAM RESPONSIBILITIES

### Developer 1 — Identity and Access Management

Services: authentication-service, user-service

Deliverables:
- JWT signing and validation infrastructure
- User registration, login, password management
- User profile CRUD operations
- Shared authentication dependencies: get_current_user, optional_current_user
- JWT token format and claims specification

Boundary: Never accesses feed_db or community_db. Provides user_id (UUID) that other services store as plain references.

### Developer 2 — Social Content and Community (YOU)

Services: feed-service, community-service

Backend: complete models, repositories, services, API endpoints for both services

Frontend:
- apps/web/src/views/Discover/ — Feed pages, post interactions, story detail
- apps/web/src/views/Communities/ — Community management interface, discussions

Database migrations: Alembic for feed_db and community_db

Media: MinIO integration for `posts` and `communities` buckets

Docker: docker-compose.yml entries for feed-service and community-service

Testing: unit and integration tests for both services

API routing: Traefik entries for /api/v1/feed/* and /api/v1/communities/*

### Developer 3 — Travel Planning and Professional Services

Services: expedition-service, guide-service

Also responsible for:
- Infrastructure setup: PostgreSQL, MinIO, Redis, Docker Compose
- Platform services: Traefik gateway configuration, monitoring setup
- Phase 2 services: recommendation, chat, notification, moderation

---

## 6. MY RESPONSIBILITIES (Developer 2)

### Backend — Feed Service (COMPLETE)

- Post CRUD with soft delete
- Social interactions: likes (idempotent), bookmarks (idempotent, private), shares (not idempotent)
- Nested comments: one level of replies only
- Media handling: MinIO presigned URL generation, object_key persistence
- REST API following canonical /api/v1/feed/* contract
- Alembic migration 001_initial.py for feed_db — COMPLETE

### Backend — Community Service (IN PROGRESS)

- Community lifecycle: create, edit, archive, soft delete
- Membership: join (public = immediate, private/approval = request flow), leave, remove, role management
- Join requests: create, list pending, approve/reject
- Community rules: create, update, delete, ordered list
- Discussion forums: create, list, get, update, soft delete
- Discussion comments: add, update, soft delete
- Community media: logo and banner presigned URL generation + persistence
- REST API following canonical /api/v1/communities/* contract
- Alembic migration for community_db — NOT YET CREATED

### Frontend (not yet started)

- apps/web/src/views/Discover/ — feed timeline, story cards, post creation, interactions, comments
- apps/web/src/views/Communities/ — community discovery, workspace, membership, discussions, rules

### Testing (not yet started)

- Feed service: test directory exists, implementations are empty stubs
- Community service: not started

### Docker (not yet done)

- Add feed-service and community-service entries to root docker-compose.yml

### Media (partially done)

- Feed service: presigned URL generation stubbed, MinIO client not integrated
- Community service: logo/banner upload endpoints not yet implemented

### Database

- feed_db: alembic/versions/001_initial.py — COMPLETE
- community_db: no migration exists yet — TO BE CREATED

### APIs

All endpoints must follow canonical prefixes: /api/v1/feed/* and /api/v1/communities/*

---

## 7. FEED SERVICE — COMPLETE REFERENCE

### Responsibilities

- Travel post lifecycle: create, publish, edit, soft delete
- Media handling: MinIO presigned URL generation, object_key persistence
- Social: likes (idempotent), bookmarks (idempotent, private), shares (not idempotent)
- Comments: create, edit, soft delete, one level of replies
- Feed listing: chronological, filtered by author/community/expedition/tags/location/date range
- Visibility enforcement: PUBLIC (all), COMMUNITY (all authenticated for now, TODO membership check), PRIVATE (author only)
- Authorization: ownership checks on all write operations

### NOT Responsible For

- User profiles (User Service)
- Community lifecycle (Community Service)
- Feed ranking/personalization (Recommendation Service, Phase 2)
- Push notifications (Notification Service, Phase 2)
- Content moderation decisions (Moderation Service, Phase 2)

### Database Tables

**posts:**
- id UUID PK
- author_id UUID — plain reference to user_db (NOT FK)
- community_id UUID nullable — plain reference to community_db (NOT FK)
- expedition_id UUID nullable — plain reference to trip_db (NOT FK)
- title String(255) NOT NULL
- content Text nullable
- location String(255) nullable
- status String(20) — PostStatus: DRAFT, PUBLISHED, ARCHIVED, DELETED
- visibility String(20) — PostVisibility: PUBLIC, COMMUNITY, PRIVATE
- is_deleted Boolean, deleted_at, deleted_by (SoftDeleteMixin)
- created_at, updated_at, created_by, updated_by (AuditMixin)
- Indexes: (author_id, created_at), (community_id, created_at), (status, visibility)

**post_media:**
- id UUID PK
- post_id UUID FK → posts.id CASCADE
- media_url String(1024) — full MinIO URL
- object_key String(1024) — MinIO key for deletion
- media_type String(20) — IMAGE (VIDEO future)
- display_order Integer — 0 = cover image
- alt_text String(255) nullable
- created_at, updated_at, created_by, updated_by (AuditMixin)
- Index: (post_id, display_order)

**post_tags:**
- id UUID PK
- post_id UUID FK → posts.id CASCADE
- tag String(50) — lowercase, trimmed
- UniqueConstraint: (post_id, tag)
- Index on tag

**likes:**
- id UUID PK
- post_id UUID FK → posts.id CASCADE
- user_id UUID — plain reference to user_db
- created_at, updated_at (TimestampMixin)
- UniqueConstraint: (post_id, user_id) — idempotent

**bookmarks:**
- id UUID PK
- post_id UUID FK → posts.id CASCADE
- user_id UUID — plain reference
- created_at, updated_at (TimestampMixin)
- UniqueConstraint: (post_id, user_id) — idempotent
- Index: (user_id, created_at)

**shares:**
- id UUID PK
- post_id UUID FK → posts.id CASCADE
- user_id UUID — plain reference
- share_channel String(50) nullable
- created_at, updated_at (TimestampMixin)
- NOT unique — a user can share multiple times

**comments:**
- id UUID PK
- post_id UUID FK → posts.id CASCADE
- author_id UUID — plain reference
- parent_comment_id UUID FK → comments.id CASCADE nullable — one level only
- content Text NOT NULL
- is_deleted Boolean, deleted_at, deleted_by (SoftDeleteMixin)
- created_at, updated_at (TimestampMixin)
- CheckConstraint: content not empty

### Business Logic Rules

- Tags are deduplicated and lowercased at service layer before persistence
- Community posts cannot have PRIVATE visibility (enforced in service)
- Only the author can edit or delete their own posts
- Like and bookmark are idempotent via insert-or-ignore on unique constraint
- Shares are NOT idempotent — each is a new event record
- Interaction counts (like_count, comment_count, share_count) are computed via aggregate queries, not stored on the post
- is_liked and is_bookmarked are computed per-request based on current_user_id
- Soft delete preserves comment threads intact

### REST API (Canonical — DO NOT DEVIATE)

```
POST   /api/v1/feed/posts
GET    /api/v1/feed/posts
GET    /api/v1/feed/posts/{post_id}
PUT    /api/v1/feed/posts/{post_id}
DELETE /api/v1/feed/posts/{post_id}

GET    /api/v1/feed/users/{user_id}/posts
GET    /api/v1/feed/communities/{community_id}/posts

POST   /api/v1/feed/posts/{post_id}/like
DELETE /api/v1/feed/posts/{post_id}/like
POST   /api/v1/feed/posts/{post_id}/bookmark
DELETE /api/v1/feed/posts/{post_id}/bookmark
GET    /api/v1/feed/me/bookmarks
POST   /api/v1/feed/posts/{post_id}/share

POST   /api/v1/feed/posts/{post_id}/comments
GET    /api/v1/feed/posts/{post_id}/comments
PUT    /api/v1/feed/comments/{comment_id}
DELETE /api/v1/feed/comments/{comment_id}
POST   /api/v1/feed/comments/{comment_id}/reply

POST   /api/v1/feed/posts/{post_id}/media/upload-url
POST   /api/v1/feed/posts/{post_id}/media
DELETE /api/v1/feed/posts/{post_id}/media/{media_id}
```

### Key Schema Classes (app/schemas/feed.py)

- PostCreateRequest: title, content, location, community_id, expedition_id, tags, visibility
- PostUpdateRequest: all optional — title, content, location, tags, visibility
- PostSchema: full post with media list, tags list, interaction counts, is_liked, is_bookmarked
- PostSummarySchema: lightweight for listing — cover_image_url, tag_list, counts
- PostListResponse: posts list, total, limit, offset, has_more
- CommentCreateRequest: content, parent_comment_id optional
- CommentSchema: recursive replies list (one level)
- LikeActionResponse: post_id, is_liked, like_count
- BookmarkActionResponse: post_id, is_bookmarked
- ShareActionResponse: post_id, share_count, share_id
- MediaUploadRequest: filename, content_type (validated to image types)
- MediaUploadResponse: upload_url, object_key, expires_in

### Service Layer Pattern

PostService takes AsyncSession, creates PostRepository + InteractionRepository + CommentRepository.
All business logic goes in service layer. Repositories are pure data access.
Repositories return ORM model instances. Services convert to Pydantic schemas.
Exception types used: NotFoundError, ForbiddenError, ValidationError (from shared.exceptions).

### Current Status

COMPLETE. All layers implemented and wired. Migration created. Service starts and health check returns 200.

---

## 8. COMMUNITY SERVICE — FULL SPECIFICATION

### Responsibilities

- Community lifecycle: create, edit, archive, soft delete
- Membership: join (public = immediate, approval-required = request flow), leave, remove member, role management (OWNER, MODERATOR, MEMBER, BANNED)
- Join requests: create, list pending, approve or reject
- Community rules: create, update, delete, ordered display list
- Discussion forums: create, list, get, update, soft delete discussions
- Discussion comments: flat comments (no nesting unlike feed), add, update, soft delete
- Community media: logo and banner — presigned URL generation + object_key persistence

### NOT Responsible For

- User profiles (User Service)
- Feed posts within community (Feed Service — posts reference community_id)
- Content moderation decisions (Moderation Service, Phase 2)
- Real-time community chat (Chat Service, Phase 2)

### Database Tables

**communities:**
- id UUID PK
- creator_id UUID — plain reference to user_db (NOT FK)
- name String(100) NOT NULL
- slug String(120) UNIQUE NOT NULL INDEX — URL-safe, auto-generated from name, numeric suffix if collision
- description Text nullable
- location String(255) nullable
- logo_url String(1024) nullable
- logo_object_key String(1024) nullable
- banner_url String(1024) nullable
- banner_object_key String(1024) nullable
- status String(20) — CommunityStatus: ACTIVE, ARCHIVED, DELETED
- visibility String(20) — CommunityVisibility: PUBLIC, PRIVATE
- requires_approval Boolean — if True, even public community requires approval to join
- member_count Integer NOT NULL default 0 — DENORMALIZED, updated by service layer
- is_deleted Boolean, deleted_at, deleted_by (SoftDeleteMixin)
- created_at, updated_at, created_by, updated_by (AuditMixin)
- Indexes: (status, visibility), (creator_id, created_at)
- Relationships: members (selectin), join_requests (select), rules (selectin ordered), discussions (select)

**community_members:**
- id UUID PK
- community_id UUID FK → communities.id CASCADE
- user_id UUID — plain reference to user_db (NOT FK)
- role String(20) — MemberRole: OWNER, MODERATOR, MEMBER, BANNED
- status String(20) — MembershipStatus: ACTIVE, LEFT, REMOVED, BANNED
- created_at, updated_at (TimestampMixin)
- UniqueConstraint: (community_id, user_id) — one record per user per community
- Indexes: user_id, (community_id, status)

**join_requests:**
- id UUID PK
- community_id UUID FK → communities.id CASCADE
- requester_id UUID — plain reference to user_db (NOT FK)
- message Text nullable — optional message from requester
- status String(20) — JoinRequestStatus: PENDING, APPROVED, REJECTED, CANCELLED
- reviewed_by UUID nullable — UUID of moderator/owner who actioned it
- created_at, updated_at, created_by, updated_by (AuditMixin)
- Indexes: (community_id, status), requester_id

**community_rules:**
- id UUID PK
- community_id UUID FK → communities.id CASCADE
- title String(255) NOT NULL
- description Text nullable
- order_index Integer NOT NULL default 1 — 1-based ascending
- created_at, updated_at, created_by, updated_by (AuditMixin)
- Index: (community_id, order_index)

**discussions:**
- id UUID PK
- community_id UUID FK → communities.id CASCADE
- author_id UUID — plain reference to user_db (NOT FK)
- title String(255) NOT NULL
- content Text nullable
- comment_count Integer NOT NULL default 0 — DENORMALIZED
- is_deleted Boolean, deleted_at, deleted_by (SoftDeleteMixin)
- created_at, updated_at, created_by, updated_by (AuditMixin)
- Indexes: (community_id, created_at), author_id

**discussion_comments:**
- id UUID PK
- discussion_id UUID FK → discussions.id CASCADE
- author_id UUID — plain reference to user_db (NOT FK)
- content Text NOT NULL
- is_deleted Boolean, deleted_at, deleted_by (SoftDeleteMixin)
- created_at, updated_at (TimestampMixin)
- CheckConstraint: LENGTH(TRIM(content)) > 0
- Indexes: (discussion_id, created_at), author_id
- NOTE: Flat structure — NO nesting (unlike feed comments which have parent_comment_id)

### Membership Business Logic Rules

- When a PUBLIC community (requires_approval=False) is joined: create CommunityMember with ACTIVE status immediately
- When a community has requires_approval=True or visibility=PRIVATE: create JoinRequest with PENDING status, do NOT create CommunityMember yet
- On join request APPROVE: create CommunityMember ACTIVE, update JoinRequest status=APPROVED, increment member_count
- On join request REJECT: update JoinRequest status=REJECTED only, do NOT create CommunityMember
- A user can only have ONE PENDING join request per community at a time (enforced at service layer)
- On leave: update CommunityMember status=LEFT, decrement member_count
- On remove by moderator: update CommunityMember status=REMOVED, decrement member_count
- On ban: update CommunityMember role=BANNED status=BANNED, decrement member_count
- Creator is always added as OWNER member when community is created (member_count starts at 1)
- OWNER role cannot be assigned via the role update endpoint

### Permission Matrix

| Action | Anonymous | Member | Moderator | Owner |
|--------|-----------|--------|-----------|-------|
| View public community | Yes | Yes | Yes | Yes |
| View private community | No | Yes | Yes | Yes |
| Join public community | Yes (must auth) | N/A | N/A | N/A |
| Request join private | Yes (must auth) | N/A | N/A | N/A |
| Edit community | No | No | No | Yes |
| Delete community | No | No | No | Yes |
| Add rule | No | No | Yes | Yes |
| Edit/delete rule | No | No | Yes | Yes |
| Approve/reject join requests | No | No | Yes | Yes |
| Remove member | No | No | Yes | Yes |
| Ban member | No | No | Yes | Yes |
| Update member role | No | No | No | Yes |
| Create discussion | No | Yes | Yes | Yes |
| Edit own discussion | No | Yes | Yes | Yes |
| Delete any discussion | No | No | Yes | Yes |
| Comment on discussion | No | Yes | Yes | Yes |
| Edit own comment | No | Yes | Yes | Yes |
| Delete any comment | No | No | Yes | Yes |

### REST API (Canonical — DO NOT DEVIATE)

```
POST   /api/v1/communities
GET    /api/v1/communities
GET    /api/v1/communities/{community_id}
PUT    /api/v1/communities/{community_id}
DELETE /api/v1/communities/{community_id}

POST   /api/v1/communities/{community_id}/logo/upload-url
POST   /api/v1/communities/{community_id}/banner/upload-url
PUT    /api/v1/communities/{community_id}/logo
PUT    /api/v1/communities/{community_id}/banner

POST   /api/v1/communities/{community_id}/join
DELETE /api/v1/communities/{community_id}/leave
GET    /api/v1/communities/{community_id}/members
DELETE /api/v1/communities/{community_id}/members/{user_id}
PUT    /api/v1/communities/{community_id}/members/{user_id}/role

GET    /api/v1/communities/{community_id}/join-requests
PUT    /api/v1/communities/join-requests/{request_id}

GET    /api/v1/communities/{community_id}/rules
POST   /api/v1/communities/{community_id}/rules
PUT    /api/v1/communities/rules/{rule_id}
DELETE /api/v1/communities/rules/{rule_id}

GET    /api/v1/communities/{community_id}/discussions
POST   /api/v1/communities/{community_id}/discussions
GET    /api/v1/communities/discussions/{discussion_id}
PUT    /api/v1/communities/discussions/{discussion_id}
DELETE /api/v1/communities/discussions/{discussion_id}
POST   /api/v1/communities/discussions/{discussion_id}/comments
PUT    /api/v1/communities/discussions/comments/{comment_id}
DELETE /api/v1/communities/discussions/comments/{comment_id}
```

### Key Schema Classes (app/schemas/community.py) — ALL IMPLEMENTED

Request schemas: CommunityCreateRequest, CommunityUpdateRequest, JoinCommunityRequest, JoinRequestActionRequest, MemberRoleUpdateRequest, CommunityRuleCreateRequest, CommunityRuleUpdateRequest, DiscussionCreateRequest, DiscussionUpdateRequest, DiscussionCommentCreateRequest, DiscussionCommentUpdateRequest, MediaUploadRequest, CommunityMediaSetRequest

Response schemas: CommunitySchema (full, includes rules + current_user_role + is_member), CommunitySummarySchema (lightweight for listing), CommunityListResponse, MemberSchema, MemberListResponse, JoinRequestSchema, JoinRequestListResponse, CommunityRuleSchema, CommunityRuleListResponse, DiscussionSchema, DiscussionSummarySchema, DiscussionListResponse, DiscussionCommentSchema, DiscussionCommentListResponse, MediaUploadResponse

Query param schemas: CommunityQueryParams, DiscussionQueryParams, CommentQueryParams, MemberQueryParams

### What Is Still Missing in Community Service

- app/repositories/community_repository.py — NOT CREATED (task interrupted)
- app/repositories/membership_repository.py — NOT CREATED
- app/repositories/discussion_repository.py — NOT CREATED
- app/repositories/__init__.py — empty
- app/services/community_service.py — NOT CREATED
- app/services/membership_service.py — NOT CREATED
- app/services/discussion_service.py — NOT CREATED
- app/services/media_service.py — NOT CREATED
- app/services/__init__.py — empty
- app/api/communities.py — NOT CREATED
- app/api/members.py — NOT CREATED
- app/api/discussions.py — NOT CREATED
- app/api/media.py — NOT CREATED
- app/api/routes.py — NOT CREATED
- app/api/__init__.py — empty
- app/core/main.py — needs routes wired in
- alembic/env.py — needs model imports added
- alembic/versions/001_initial.py — NOT CREATED
- requirements.txt — needs python-multipart added

---

## 9. FRONTEND

### Status

The entire frontend (`apps/web/`) is a skeleton. Only `package.json` exists. No implementation has started.

### Developer 2 Frontend Responsibilities

**Discover (Feed) Views — `apps/web/src/views/Discover/`:**
- Feed timeline with infinite scroll (chronological, public posts)
- Story cards: cover image, title, author, location, tags, interaction counts
- Story detail modal: full content, all media, comments, reply UI
- Post creation/editing interface with tag input and visibility selector
- Like, bookmark, share buttons with optimistic UI updates
- Comment threading: root comments + one level replies
- User profile mini-view linking to User Service data

**Communities Views — `apps/web/src/views/Communities/`:**
- Community discovery listing with search and location filter
- Individual community workspace: about, rules, members, discussions
- Membership flow: join button (public), request form (private)
- Discussion forum: list, create, view thread, add comment
- Community management panel (owner only): edit info, manage members, manage rules
- Join request management (moderator/owner): list pending, approve/reject

### API Integration Pattern

All API calls go through TanStack Query + Axios. Base URL is the Traefik gateway. Auth token is passed as `Authorization: Bearer {token}` header on every authenticated request. The `optional_current_user` dependency handles unauthenticated browsing.

### Backend Mapping

- Discover feed → GET /api/v1/feed/posts
- Post detail → GET /api/v1/feed/posts/{post_id}
- Create post → POST /api/v1/feed/posts
- Like → POST/DELETE /api/v1/feed/posts/{post_id}/like
- Bookmark → POST/DELETE /api/v1/feed/posts/{post_id}/bookmark
- Comments → GET/POST /api/v1/feed/posts/{post_id}/comments
- Community list → GET /api/v1/communities
- Community detail → GET /api/v1/communities/{community_id}
- Join → POST /api/v1/communities/{community_id}/join
- Discussions → GET/POST /api/v1/communities/{community_id}/discussions

---

## 10. DATABASE ARCHITECTURE

### Database-per-Service Rule

Each service has exactly one PostgreSQL database. No service ever connects to another service's database. Cross-service data needs are satisfied by:
1. Storing a plain UUID reference (e.g., `author_id` in posts references user_db but is just a UUID column, not a FK)
2. Making HTTP API calls to the owning service to enrich data at the application layer
3. Kafka events for async propagation (Phase 2)

### External IDs Pattern

Any UUID that references a record in a different service's database is stored as a plain `UUID` column with NO ForeignKey constraint. Examples:
- `posts.author_id` — references user_db, stored as plain UUID
- `posts.community_id` — references community_db, stored as plain UUID
- `community_members.user_id` — references user_db, stored as plain UUID
- `discussions.author_id` — references user_db, stored as plain UUID

The application service layer is responsible for referential integrity, not the database.

### Internal FKs

ForeignKey constraints ARE used for relationships within the same database. Examples:
- `post_media.post_id` → `posts.id` CASCADE (same DB)
- `community_members.community_id` → `communities.id` CASCADE (same DB)
- `discussions.community_id` → `communities.id` CASCADE (same DB)

### Shared Base Classes (shared/database.py)

```python
class Base(DeclarativeBase): pass

class TimestampMixin:
    created_at: Mapped[datetime]  # timezone-aware, auto-set
    updated_at: Mapped[datetime]  # timezone-aware, auto-updated

class SoftDeleteMixin:
    is_deleted: Mapped[bool]          # default False
    deleted_at: Mapped[Optional[datetime]]
    deleted_by: Mapped[Optional[uuid.UUID]]

class AuditMixin(TimestampMixin):
    created_by: Mapped[Optional[uuid.UUID]]
    updated_by: Mapped[Optional[uuid.UUID]]
```

### Alembic Strategy

- One `alembic/` directory per service, one `alembic.ini` per service
- `alembic/env.py` imports ALL models from `app/models/__init__.py` for autodiscovery
- `alembic/env.py` sets `sqlalchemy.url` from `settings.DATABASE_URL` at runtime
- Migration naming: `{NNN}_{description}.py` e.g. `001_initial.py`
- One migration per checkpoint (not per table)
- Migrations use `asyncio.run(run_migrations_online())` for async engine
- `alembic.ini` has `prepend_sys_path = .` so the service root is on sys.path

### Running Migrations

```bash
# From service root directory
cd services/community-service
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

Requires the database to exist and DATABASE_URL env var to be set (or .env file present).

---

## 11. SERVICE BOUNDARIES

### Feed vs User Service

- Feed Service stores `author_id` as a plain UUID
- Feed Service does NOT call User Service in Phase 1 (no author info enrichment yet)
- In Phase 2: Feed Service will call User Service to enrich post responses with author display name and avatar
- User Service never queries feed_db

### Feed vs Community Service

- Feed Service stores `community_id` as a plain UUID on posts
- Feed Service has a `GET /api/v1/feed/communities/{community_id}/posts` endpoint
- Feed Service does NOT check community membership when serving community posts (Phase 1 simplification)
- Community Service never queries feed_db
- Community Service does NOT own or manage posts — that belongs to Feed Service

### Feed vs Recommendation Service

- Recommendation Service (Phase 2) will consume Kafka events from Feed Service (post.created, interaction.liked)
- Recommendation Service will return ranked lists of post IDs
- Feed Service will accept an optional ranked_ids parameter to serve personalized feeds
- No direct database access between them

### Community vs User Service

- Community Service stores `creator_id` and `user_id` in members as plain UUIDs
- Community Service does NOT call User Service in Phase 1
- In Phase 2: Community Service will call User Service to enrich member listings with display names
- User Service never queries community_db

### Community vs Moderation Service

- Moderation Service (Phase 2) will receive events when content is reported
- Community Service will receive events when a user is banned platform-wide
- No direct database access between them

### Community vs Expedition Service

- Expedition Service may reference `community_id` as a plain UUID (expeditions can belong to communities)
- Community Service does NOT own expedition data
- No direct database access between them

### The Hard Rule

**No service ever does a database query against another service's database.**
**No service ever does a JOIN across service databases.**
**The only valid cross-service data access is: HTTP API call or Kafka event.**

---

## 12. AUTHENTICATION

### JWT Architecture

- Authentication Service is the ONLY service that generates JWTs
- All other services only validate JWTs using the shared secret
- JWT secret is in `CommonSettings.JWT_SECRET` (environment variable)
- JWT algorithm is in `CommonSettings.JWT_ALGORITHM` (default HS256)

### Shared Dependencies (shared/dependencies.py)

```python
async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    # Validates Bearer token, returns JWT payload dict
    # Raises UnauthorizedException if missing or invalid

async def optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    # Returns JWT payload if valid token present, None if not
    # Does NOT raise — used for endpoints that work for both auth and anon users

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    # Gets session from app.state.db_sessionmaker
    # Commits on success, rollbacks on exception
```

### How Services Use Current User

In feed-service and community-service:
- Endpoints that require authentication: `current_user_id: uuid.UUID = Depends(get_current_user)`
- Endpoints that work anonymously: `current_user_id: Optional[uuid.UUID] = Depends(optional_current_user)`
- The JWT payload's `sub` field contains the user UUID as a string
- Services extract the user ID from the payload and use it as a UUID

IMPORTANT: The actual `get_current_user` returns the full JWT payload dict. In the feed service the router extracts `current_user_id` directly as `uuid.UUID`. Check the actual feed service API files for exact usage pattern.

### Authorization Pattern

Business logic authorization (ownership checks) is done in the SERVICE layer, not the repository layer and not FastAPI dependencies. Pattern:

```python
# In service method:
post = await self.post_repo.get_by_id(post_id)
if not post:
    raise NotFoundError(f"Post {post_id} not found")
if post.author_id != current_user_id:
    raise ForbiddenError("You can only edit your own posts")
```

### Exception Aliases (shared/exceptions.py)

These short-form aliases exist and are used throughout the services:

```python
NotFoundError = NotFoundException        # HTTP 404
ForbiddenError = ForbiddenException      # HTTP 403
ValidationError = ValidationException   # HTTP 422
ConflictError = ConflictException        # HTTP 409
UnauthorizedError = UnauthorizedException # HTTP 401
```

The `register_exception_handlers(app)` call in main.py registers handlers that convert these to proper JSON error responses.

### Developer 1 Dependency

Until Developer 1 completes the Authentication Service, JWT tokens cannot be generated. For local development and testing, hardcode a test JWT or mock `get_current_user`. The shared library's `decode_jwt_token` utility is already implemented and will work once the secret is configured.

---

## 13. KAFKA

### Phase 1 Status

Kafka is NOT used in Phase 1. All communication is synchronous REST. Kafka dependencies are installed in requirements.txt but no producer or consumer code exists in any service.

### Phase 2 Planned Topics (shared/constants/topics.py)

The `KafkaTopic` enum is defined. Planned topics include:
- `post.created` — published by Feed Service when a post is published
- `post.deleted` — published by Feed Service on soft delete
- `interaction.liked` — published by Feed Service on like
- `community.member_joined` — published by Community Service
- `community.member_left` — published by Community Service
- `moderation.user_banned` — published by Moderation Service

### Phase 2 Consumers

- Recommendation Service: consumes post.created, interaction.liked to build interest profiles
- Notification Service: consumes all events to generate user notifications
- Moderation Service: consumes content report events

### Kafka Configuration

CommonSettings contains `KAFKA_BOOTSTRAP_SERVERS` and related config. KRaft mode (no ZooKeeper) is planned. Kafka container stub exists in docker-compose.yml.

---

## 14. MINIO

### Bucket Design

- Bucket `posts` — owned by Feed Service — stores post images
- Bucket `communities` — owned by Community Service — stores logos and banners

### Upload Flow

1. Client calls service endpoint: `POST /api/v1/feed/posts/{post_id}/media/upload-url`
2. Service generates a MinIO presigned PUT URL (valid 1 hour) and an object_key
3. Service returns `{ upload_url, object_key, expires_in: 3600 }`
4. Client uploads the binary file directly to MinIO using the presigned URL (no service in the loop)
5. Client calls service endpoint with the `object_key`: `POST /api/v1/feed/posts/{post_id}/media`
6. Service stores `{ media_url, object_key, display_order, alt_text }` in PostgreSQL

### Object Key Pattern

- Feed posts: `posts/{post_id}/{uuid}.{ext}`
- Community logos: `communities/{community_id}/logo/{uuid}.{ext}`
- Community banners: `communities/{community_id}/banner/{uuid}.{ext}`

### Current Implementation Status

- Feed service `media_service.py` exists but presigned URL generation is STUBBED — returns placeholder URL string
- MinIO Python SDK (`minio`) is not yet in requirements.txt for either service
- Community service has no media service yet
- MinIO bucket initialization script does not exist

### Media Metadata in PostgreSQL

Binary data is NEVER stored in PostgreSQL. Only:
- `media_url` — the full public URL to the stored object
- `object_key` — the MinIO object key used for deletion when the post/community is deleted

---

## 15. REPOSITORY ANALYSIS

### Confirmed Discoveries

These were confirmed by direct file system inspection and file reading during the previous session:

1. Feed service is fully implemented and follows a clean 4-layer architecture (model → repository → service → API)
2. All 10 services have identical directory structures with the same boilerplate
3. The shared library is well-designed and provides everything needed for service implementation
4. `shared/exceptions.py` originally did NOT have short-form aliases (NotFoundError etc.) — these were ADDED during the previous session
5. `shared/__init__.py` now exports the aliases
6. Community service models and schemas were written to exactly mirror feed service patterns
7. The `optional_current_user` dependency exists in `shared/dependencies.py` but was NOT originally exported from `shared/__init__.py` — verify before using
8. Feed service `get_current_user` returns the full JWT payload dict, not just the user ID — the API endpoints handle the extraction

### Documentation Inconsistencies Found

- Some internal docs reference `stories` terminology — this is wrong. The canonical term is `posts`. The API uses `/api/v1/feed/posts`.
- Some internal docs reference `/api/v1/community/` (singular) — this is wrong. The canonical prefix is `/api/v1/communities/` (plural).
- The canonical API contracts listed in sections 7 and 8 of this document are the source of truth.

### Architecture Observations

- Feed service `post_service.py` is 17KB — it is the largest and most complex file. Read it carefully before implementing community_service.py.
- The repository pattern passes `AsyncSession` directly to repository constructors — no abstract base class is used.
- Services instantiate repositories directly (not injected). This is intentional and consistent throughout.
- The `selectin` lazy loading strategy is used for relationships that are always needed (rules loaded with community). The `select` strategy is used for relationships loaded on demand (members, discussions).
- `member_count` and `comment_count` are denormalized counters. They must be kept in sync by the service layer on every membership change and comment add/delete.
- The alembic `env.py` pattern is identical across services: import all models, set URL from settings, run async.

### Skeleton Services

All skeleton services (authentication, user, expedition, guide, recommendation, chat, notification, moderation) have:
- Working FastAPI app in `app/core/main.py` with health check endpoint
- Database engine and session configured
- Settings loaded from environment
- Empty `__init__.py` files in models/, schemas/, repositories/, services/, api/
- Dockerfile present and functional
- alembic.ini and empty alembic/env.py

---

## 16. CHECKPOINT ROADMAP

### Checkpoint 1 — Community Service Backend Core (CURRENT)

**Objective:** Complete the full community service backend so it runs and serves all API endpoints.

**Deliverables:**
- Community service models (DONE)
- Community service Pydantic schemas (DONE)
- Community repository: CommunityRepository, MembershipRepository, DiscussionRepository
- Community services: CommunityService, MembershipService, DiscussionService, MediaService
- Community API routers: communities.py, members.py, discussions.py, media.py
- Wire up app/api/routes.py and update app/core/main.py
- Update alembic/env.py with model imports
- Create alembic/versions/001_initial.py migration
- Update requirements.txt

**Dependencies:** shared library (done), community models (done), community schemas (done)

**Complexity:** High — membership state machine, permission checks, denormalized counters

**Current status:** Tasks 1-3 of 9 complete. Task 4 (repositories) was interrupted.

### Checkpoint 2 — Community Service Testing and Docker

**Objective:** Test coverage and containerization for community service.

**Deliverables:**
- Unit tests for all service methods
- Integration tests for API endpoints
- docker-compose.yml entry for community-service
- .env.example updated

**Dependencies:** Checkpoint 1 complete

### Checkpoint 3 — Feed Service Docker and Testing

**Objective:** Retrofit Docker integration and test coverage for feed service.

**Deliverables:**
- docker-compose.yml entry for feed-service
- Unit tests for PostService, CommentService
- Integration tests for post and interaction endpoints

**Dependencies:** Feed service complete (already done)

### Checkpoint 4 — MinIO Integration

**Objective:** Replace stubbed presigned URL generation with real MinIO SDK calls.

**Deliverables:**
- MinIO Python SDK added to both services' requirements.txt
- Real presigned URL generation in feed-service media_service.py
- Real presigned URL generation in community-service media_service.py
- MinIO bucket initialization script

**Dependencies:** MinIO container running (Dev 3 infrastructure)

### Checkpoint 5 — Frontend: Discover Feed

**Objective:** Implement the Discover feed views.

**Deliverables:**
- apps/web/src/views/Discover/ complete
- Feed timeline, story cards, post detail
- Like, bookmark, share UI
- Comment thread UI
- Post creation form

**Dependencies:** Checkpoint 1, Checkpoint 3, Developer 1 auth frontend for login state

### Checkpoint 6 — Frontend: Communities

**Objective:** Implement the Communities views.

**Deliverables:**
- apps/web/src/views/Communities/ complete
- Community listing, community workspace
- Membership join flow
- Discussion forum UI

**Dependencies:** Checkpoint 1, Checkpoint 2, Checkpoint 5

---

## 17. CURRENT PROJECT STATUS

### Exactly Where Development Stands

**What is complete:**
- Feed Service: 100% — models, schemas, repositories, services, API endpoints, alembic migration, all wired up
- Shared library exceptions: NotFoundError/ForbiddenError/ValidationError/ConflictError/UnauthorizedError aliases added
- Community Service models: Community, CommunityMember, JoinRequest, CommunityRule, Discussion, DiscussionComment — all 6 models written and exported from `__init__.py`
- Community Service schemas: all request/response/query param schemas written and exported from `__init__.py`

**What was interrupted:**
- Community Service repositories: `app/repositories/community_repository.py` was being written. The file creation call was interrupted mid-tool-use. The file may be partially written or empty — verify before proceeding.

**What has not been started:**
- Community repositories (membership_repository.py, discussion_repository.py)
- Community services
- Community API endpoints
- Community alembic migration
- Community main.py route wiring
- All frontend work
- All Docker compose entries
- All test implementations

**Current Git Branch:** Not confirmed. Assume `main` or a feature branch. Run `git status` to verify.

**Current Checkpoint:** Checkpoint 1 — Community Service Backend Core

**Task progress within checkpoint:** 3 of 9 tasks confirmed complete, task 4 (repositories) was in progress when interrupted.

### What Remains Before Checkpoint 1 Is Complete

In order:
1. Verify/create `app/repositories/community_repository.py`
2. Create `app/repositories/membership_repository.py`
3. Create `app/repositories/discussion_repository.py`
4. Update `app/repositories/__init__.py`
5. Create `app/services/community_service.py`
6. Create `app/services/membership_service.py`
7. Create `app/services/discussion_service.py`
8. Create `app/services/media_service.py`
9. Update `app/services/__init__.py`
10. Create `app/api/communities.py`
11. Create `app/api/members.py`
12. Create `app/api/discussions.py`
13. Create `app/api/media.py`
14. Create `app/api/routes.py`
15. Update `app/api/__init__.py`
16. Update `app/core/main.py` to include api_router
17. Update `alembic/env.py` to import all community models
18. Create `alembic/versions/001_initial.py` migration
19. Update `requirements.txt`

---

## 18. IMPORTANT DECISIONS

### API Contracts

- The 6 canonical API prefixes are fixed and agreed by the full team (listed in section 7 and 8)
- The singular `/api/v1/community/` form is wrong — always use plural `/api/v1/communities/`
- The term `stories` in documentation is wrong — always use `posts`
- Feed endpoint: `/api/v1/feed/comments/{comment_id}/reply` — replies are created through the comments endpoint with a `parent_comment_id` in the body, not via a separate nested route

### Naming Conventions

- Python files: snake_case
- Classes: PascalCase
- Database tables: snake_case plural (communities, community_members)
- API endpoints: kebab-case for multi-word path segments (join-requests, upload-url)
- Pydantic schemas: PascalCase with suffix describing role (CreateRequest, UpdateRequest, Schema, SummarySchema, ListResponse)
- Repository classes: PascalCase + Repository (CommunityRepository, MembershipRepository)
- Service classes: PascalCase + Service (CommunityService, MembershipService)

### Database Ownership

- Each service owns exactly one database
- No cross-service ForeignKey constraints — ever
- External IDs are plain UUID columns
- Denormalized counters (member_count, comment_count) are maintained by service layer, not database triggers

### Implementation Strategy

- Feed Service is the canonical reference — replicate its patterns exactly
- Repository layer: pure data access, returns ORM model instances
- Service layer: business logic, authorization checks, converts models to Pydantic schemas
- API layer: thin, validates input with Pydantic, calls service, catches exceptions
- Exceptions raised in service layer, caught in API layer and converted to HTTPException

### Backend-First Workflow

Backend for each service is fully implemented and tested before any frontend work begins.

### Checkpoint Workflow

Each checkpoint produces a fully working, runnable deliverable. No partial implementations merged.

### Service Boundaries

Strictly enforced: no cross-service DB access, no cross-service imports, communication via HTTP API or Kafka only.

### Coding Conventions

- Async/await throughout — no synchronous SQLAlchemy calls
- SQLAlchemy 2.0 style — `Mapped[type]` and `mapped_column()` syntax throughout
- All UUIDs use `UUID(as_uuid=True)` column type
- All datetime fields use `DateTime(timezone=True)`
- `selectin` loading for always-needed relationships, `select` for on-demand
- Service methods take Pydantic request schemas as input, return Pydantic response schemas as output
- `Optional[uuid.UUID]` return type from `optional_current_user` dependency

---

## 19. KNOWN ISSUES

### Repository Issues

- `app/repositories/community_repository.py` may be partially written or empty — verify its contents before starting task 4
- `optional_current_user` may not be exported from `shared/__init__.py` — verify and add if missing

### Documentation Issues

- Inconsistent use of `stories` vs `posts` throughout Docs/ directory — canonical term is `posts`
- Inconsistent use of singular `/community/` vs plural `/communities/` — canonical is plural
- Some docs reference Traefik config that does not exist yet

### Open Questions

- How does `get_current_user` return the user_id — as a string or UUID? The feed service API files handle this — read them carefully before implementing community API endpoints.
- MinIO bucket names confirmed? (`posts` and `communities` assumed — verify with Dev 3)
- Is python-multipart needed for file upload endpoints? Add to requirements.txt if needed.

### Risks

- Developer 1 (auth service) not complete — JWT tokens cannot be generated for real testing. Use mocked tokens in development.
- MinIO not configured with real credentials — media endpoints will fail until Dev 3 sets up infrastructure.
- No CI/CD pipeline — no automated checks on code quality.

---

## 20. COMPLETE CONVERSATION MEMORY

### Session 1 — Repository Exploration and Planning

1. Received the full OntDekker project handover document. Confirmed role as Developer 2.
2. Explored repository structure at `/Users/prajwalnaganagoudar/Desktop/OntDekkers/`.
3. Confirmed feed-service is fully implemented (all 7 tables, all layers, migration done).
4. Confirmed community-service is a skeleton — basic FastAPI app only, empty business logic directories.
5. Confirmed shared library has Base, TimestampMixin, AuditMixin, SoftDeleteMixin, CommonSettings, get_db, get_current_user, etc.
6. Read all feed service implementation files to understand the exact patterns to replicate.
7. Key discovery: `shared/exceptions.py` had `NotFoundException`, `ForbiddenException` etc. but NOT the short-form aliases `NotFoundError`, `ForbiddenError` etc. that the feed service's service layer imports. Added aliases.
8. Key discovery: `shared/__init__.py` needed updating to export the new aliases. Done.

### Session 1 — Community Service Implementation Started

9. Created task list: 9 tasks for community service implementation.
10. **Task 1 (DONE):** Added exception aliases to shared/exceptions.py and shared/__init__.py.
11. **Task 2 (DONE):** Created community service models:
    - `app/models/community.py` — Community with slug, member_count, visibility, requires_approval, logo/banner URLs
    - `app/models/membership.py` — CommunityMember (role + status), JoinRequest (with reviewed_by)
    - `app/models/rule.py` — CommunityRule with order_index
    - `app/models/discussion.py` — Discussion with denormalized comment_count, DiscussionComment (flat, no nesting)
    - `app/models/__init__.py` — exports all 6 models
12. **Task 3 (DONE):** Created community service Pydantic schemas in `app/schemas/community.py` and `app/schemas/__init__.py`. Covers all request, response, and query param schemas for all entities.
13. **Task 4 (INTERRUPTED):** Started creating `app/repositories/community_repository.py`. The file creation was cancelled mid-tool-use. Repository file may be partially written or empty.

### Key Architecture Decisions Made During Session

- Community service follows feed service patterns exactly (same 4-layer architecture)
- Slug is auto-generated from name with numeric suffix collision handling
- `member_count` is denormalized — updated by service layer on every membership change
- Discussion comments are FLAT (no parent_comment_id) unlike feed comments which support one level of nesting
- `requires_approval=True` on public communities creates a join-request flow even for public visibility
- On community creation, creator is automatically added as OWNER with member_count=1
- OWNER role cannot be assigned via the role update endpoint (enforced in schema validator)
- Permission matrix was designed and documented (see section 8)

---

## 21. CONTINUATION INSTRUCTIONS

### Where We Stopped

Task 4 of 9 was in progress when the previous session ended. The file `app/repositories/community_repository.py` was being created when the tool use was cancelled. The file may be empty or partially written.

### Which Checkpoint

Checkpoint 1 — Community Service Backend Core.

### What Has Already Been Completed

- Task 1: Exception aliases in shared/exceptions.py and shared/__init__.py
- Task 2: All 6 community service models (community.py, membership.py, rule.py, discussion.py, __init__.py)
- Task 3: All community service schemas (community.py, __init__.py)

### What Remains To Be Done

In strict order:

**Task 4 — Repositories:**
- First: check if `app/repositories/community_repository.py` exists and has content. If empty or missing, create it.
- Create `app/repositories/community_repository.py` — CommunityRepository: create (with slug generation + owner member creation), get_by_id (with rules selectin), get_by_slug, update, soft_delete, update_member_count, list_communities (with filters), update_logo, update_banner
- Create `app/repositories/membership_repository.py` — MembershipRepository: get_member, add_member, update_member_role, update_member_status, list_members (with role filter, pagination), create_join_request, get_pending_join_request, get_join_request_by_id, update_join_request_status, list_join_requests
- Create `app/repositories/discussion_repository.py` — DiscussionRepository: create_discussion, get_discussion_by_id, list_discussions (pagination), update_discussion, soft_delete_discussion, increment_comment_count, decrement_comment_count, create_comment, get_comment_by_id, list_comments (pagination), update_comment, soft_delete_comment
- Update `app/repositories/__init__.py` to export all 3 repositories

**Task 5 — Services:**
- Create `app/services/community_service.py` — CommunityService: create_community, get_community (with current_user_role and is_member enrichment), update_community, delete_community, list_communities
- Create `app/services/membership_service.py` — MembershipService: join_community (handles both immediate join and join request flow), leave_community, list_members, remove_member, update_member_role, list_join_requests, action_join_request (approve/reject)
- Create `app/services/discussion_service.py` — DiscussionService: create_discussion, get_discussion, list_discussions, update_discussion, delete_discussion, create_comment, update_comment, delete_comment, list_comments
- Create `app/services/media_service.py` — MediaService: generate_logo_upload_url, generate_banner_upload_url, set_community_logo, set_community_banner (stubbed like feed service)
- Update `app/services/__init__.py`

**Task 6 — API Endpoints:**
- Create `app/api/communities.py` — community CRUD endpoints
- Create `app/api/members.py` — membership and join request endpoints
- Create `app/api/discussions.py` — discussion and comment endpoints
- Create `app/api/media.py` — logo/banner upload URL and set endpoints
- Create `app/api/routes.py` — combines all 4 routers under prefix /api/v1/communities
- Update `app/api/__init__.py`

**Task 7 — Wire Up:**
- Update `app/core/main.py` to import and include `api_router` (same pattern as feed service)
- Update `alembic/env.py` to import all 6 community models (same pattern as feed service's env.py)

**Task 8 — Migration:**
- Run `alembic revision --autogenerate -m "initial"` OR manually create `alembic/versions/001_initial.py`
- The migration must create: communities, community_members, join_requests, community_rules, discussions, discussion_comments tables with all indexes and constraints

**Task 9 — Requirements:**
- Add `python-multipart` if needed for file upload form data
- Verify all deps are present for the implemented code

### Files Expected To Be Modified Next

```
services/community-service/app/repositories/community_repository.py   CREATE
services/community-service/app/repositories/membership_repository.py  CREATE
services/community-service/app/repositories/discussion_repository.py  CREATE
services/community-service/app/repositories/__init__.py                UPDATE
services/community-service/app/services/community_service.py          CREATE
services/community-service/app/services/membership_service.py         CREATE
services/community-service/app/services/discussion_service.py         CREATE
services/community-service/app/services/media_service.py              CREATE
services/community-service/app/services/__init__.py                    UPDATE
services/community-service/app/api/communities.py                     CREATE
services/community-service/app/api/members.py                         CREATE
services/community-service/app/api/discussions.py                     CREATE
services/community-service/app/api/media.py                           CREATE
services/community-service/app/api/routes.py                          CREATE
services/community-service/app/api/__init__.py                        UPDATE
services/community-service/app/core/main.py                           UPDATE
services/community-service/alembic/env.py                             UPDATE
services/community-service/alembic/versions/001_initial.py            CREATE
services/community-service/requirements.txt                           UPDATE
```

### Dependencies To Consider

- Read `services/feed-service/app/repositories/post_repository.py` and `interaction_repository.py` before writing community repositories — they are the canonical reference for async SQLAlchemy patterns used in this project.
- Read `services/feed-service/app/services/post_service.py` before writing community services — it shows exactly how service layer authorization, enrichment, and schema conversion work.
- Read `services/feed-service/app/api/posts.py` before writing community API endpoints — it shows the exact pattern for exception handling (try/except NotFoundError → HTTPException).
- Read `services/feed-service/app/core/main.py` and `alembic/env.py` — the community service versions should be nearly identical.
- The `shared/dependencies.py` `get_current_user` function — confirm whether it returns a dict or UUID before implementing API endpoints.

### What Should Be Implemented First

Start with Task 4 — the repositories. Check if `app/repositories/community_repository.py` has content first. If empty, implement it fresh. Then proceed in order through Tasks 4 → 5 → 6 → 7 → 8 → 9.

---

From this point onward, I will continue exactly from where the previous conversation ended without repeating repository onboarding or architectural analysis unless explicitly requested.
