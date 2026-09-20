# OntDekker Frontend–Backend Integration & Microservices Architecture

> **Version:** 1.0  
> **Document Type:** Frontend–Backend Integration Blueprint  
> **Role:** Senior Solutions Architect  
> **Purpose:** Define how every OntDekker frontend module communicates with the distributed microservices architecture, including synchronous APIs, asynchronous event pipelines, caching strategies, object storage, validation rules, and system-wide infrastructure.

---

# Table of Contents

1. System Architecture Overview
2. Global Infrastructure
3. Authentication Architecture
4. Media Storage Architecture
5. API Communication Standards
6. Discover Module Integration
7. Communities Module Integration
8. Expedition Module Integration
9. Guides Module Integration
10. Messenger Module Integration
11. Profile Module Integration
12. Caching Strategy
13. Kafka Event Architecture
14. Object Storage Architecture
15. Validation & Error Handling
16. Complete Request Lifecycle

---

# 1. System Architecture Overview

OntDekker follows a **microservices-first architecture**, where every functional domain is independently deployed, owns its own database, and communicates through a combination of synchronous REST APIs and asynchronous Kafka events.

```
Client Application
        │
        ▼
 Traefik API Gateway
        │
        ├──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
 Authentication   Feed Service   Community   Expedition
        │              │              │              │
        ▼              ▼              ▼              ▼
 Recommendation   Guide Service   Chat Service   User Service
        │
        ▼
 Notification Service
```

---

# 2. Global Infrastructure

## API Gateway

All client requests pass through **Traefik API Gateway**.

Responsibilities:

- Request routing
- JWT validation
- Rate limiting
- SSL termination
- Service discovery
- Load balancing

---

## Communication Types

### REST

Used when immediate consistency is required.

Examples:

- Login
- Fetch profile
- Join expedition
- Send message
- Update gear

---

### Kafka

Used for asynchronous processing.

Examples:

- Feed personalization
- Reputation updates
- Notifications
- Analytics
- Recommendation indexing

---

# 3. Authentication Architecture

Authentication is handled exclusively by the **Authentication Service**.

---

## Client Flow

```
Client

↓

JWT

↓

Authorization Header

↓

Gateway

↓

Authentication Service
```

---

## Authorization Header

```http
Authorization: Bearer <JWT>
```

---

## JWT Blacklist

Redis stores revoked tokens.

```
jwt:blacklist:{token_jti}
```

TTL equals the remaining token lifetime.

---

# 4. Media Storage Architecture

Large media files bypass application services using **MinIO** and pre-signed URLs.

---

## Upload Flow

```
Client

↓

Request Presigned URL

↓

Upload Directly to MinIO

↓

Store Object URL

↓

Database
```

---

## CDN Structure

```
https://cdn.ontdekker.com/

{bucket}/{object}
```

---

# 5. API Communication Standards

## Request Flow

```
Frontend

↓

API Gateway

↓

Microservice

↓

Database

↓

Response
```

---

## Error Format

Every API returns a standardized error object.

```json
{
  "status": 404,
  "error": "Not Found",
  "message": "Requested resource does not exist"
}
```

---

# 6. Discover Module Integration

## Purpose

Serve personalized editorial travel stories and social interactions.

---

## Primary APIs

| Method | Endpoint | Service |
|---------|----------|----------|
| GET | `/api/v1/feed/personalized` | Recommendation Service |
| POST | `/api/v1/posts/{id}/like` | Feed Service |
| POST | `/api/v1/posts/{id}/comment` | Feed Service |
| POST | `/api/v1/posts/{id}/save` | Feed Service |

---

## Database

```
feed_db

posts

likes

comments

saves
```

---

## Redis Cache

```
feed:personalized:{userId}
```

TTL

```
5 Minutes
```

---

## Kafka Events

Producer

```
Feed Service
```

Events

- story_interacted
- comment_added

Consumers

- Recommendation Service
- Notification Service
- User Service

---

## Object Storage

Bucket

```
stories
```

Path

```
stories/{postId}/{image}.jpg
```

---

## Validation

- Comment length: **1–1000 characters**
- 404 for invalid post
- 403 for unauthorized comment deletion

---

# 7. Communities Module Integration

## Purpose

Manage slow-travel communities, discussions, and memberships.

---

## Primary APIs

| Method | Endpoint | Service |
|---------|----------|----------|
| GET | `/api/v1/communities` | Community Service |
| GET | `/api/v1/communities/{id}` | Community Service |
| POST | `/api/v1/communities/{id}/join` | Community Service |
| GET | `/api/v1/communities/{id}/discussions` | Community Service |

---

## Database

```
community_db

communities

members

discussions

rules
```

---

## Kafka

Producer

Community Service

Event

```
community_membership_changed
```

Consumers

- Recommendation Service
- User Service

---

## Redis

```
community:details:{communityId}
```

TTL

```
15 Minutes
```

---

## Storage

Bucket

```
communities
```

Path

```
banners/{communityId}.jpg
```

---

## Validation

- Unique community names
- Role-based permissions
- 409 Conflict on duplicate names
- 403 Forbidden for restricted discussions

---

# 8. Expedition Module Integration

## Purpose

Coordinate collaborative trip planning, gear management, and expedition participation.

---

## Primary APIs

| Method | Endpoint | Service |
|---------|----------|----------|
| GET | `/api/v1/expeditions/{id}` | Expedition Service |
| POST | `/api/v1/expeditions/{id}/join` | Expedition Service |
| PUT | `/api/v1/expeditions/{id}/gear` | Expedition Service |

---

## Database

```
trip_db

expeditions

participants

gear_items

gallery
```

---

## Gear Classification

| Base Weight | Category |
|-------------|----------|
| Lowest | Ultralight |
| Low | Lightweight |
| Medium | Standard |
| Highest | Heavy |

---

## Kafka

Producer

```
expedition_completed
```

Consumers

- User Service
- Guide Service

---

## Storage

Bucket

```
expeditions
```

Gallery

```
gallery/{expeditionId}/{photo}.jpg
```

---

## Validation

- Non-negative gear weights
- Approved participants only
- 403 Forbidden for unauthorized gallery access

---

# 9. Guides Module Integration

## Purpose

Manage verified guide discovery, relationships, certifications, and reviews.

---

## Primary APIs

| Method | Endpoint | Service |
|---------|----------|----------|
| GET | `/api/v1/guides` | Guide Service |
| GET | `/api/v1/guides/me/relationships` | Guide Service |
| POST | `/api/v1/guides/{id}/reconnect` | Guide Service / Chat Service |

---

## Database

```
guide_db

guides

guide_relationships

reviews
```

---

## Kafka

Producer

```
guide_reconnection_requested
```

Consumers

- Chat Service
- Notification Service

---

## Redis

```
guides:search:{filterHash}
```

TTL

```
10 Minutes
```

---

## Storage

Bucket

```
guides
```

Credential Path

```
credentials/{guideId}/license.pdf
```

---

## Validation

- Reviews only after shared expeditions
- Ratings limited to **1–5**
- 403 Forbidden for unauthorized reviews

---

# 10. Messenger Module Integration

## Purpose

Provide real-time private, community, and expedition messaging.

---

## Communication

REST + WebSockets

---

## Primary APIs

| Method | Endpoint | Service |
|---------|----------|----------|
| GET | `/api/v1/chat/conversations` | Chat Service |
| GET | `/api/v1/chat/conversations/{id}/messages` | Chat Service |
| WS | `/api/v1/chat/ws` | Chat Service |

---

## Database

```
chat_db

conversations

participants

messages
```

---

## WebSocket Flow

```
Client

↓

JWT Handshake

↓

Chat Service

↓

Redis Pub/Sub

↓

Connected Clients
```

---

## Kafka

Producer

```
message_sent
```

Consumers

- Notification Service
- Guide Service

---

## Redis

```
chat:user:active_server:{userId}
```

Routes active socket connections across server instances.

---

## Storage

Bucket

```
chat
```

Attachments

```
attachments/{conversationId}/{file}.png
```

---

## Validation

- JWT required during handshake
- Unauthorized connections close with **4401**
- Conversation access restricted to participants

---

# 11. Profile Module Integration

## Purpose

Manage user identity, interests, badges, and preferences.

---

## Primary APIs

| Method | Endpoint | Service |
|---------|----------|----------|
| GET | `/api/v1/users/{username}` | User Service |
| PUT | `/api/v1/users/me` | User Service |

---

## Database

```
user_db

profiles

interests

badges
```

---

## Kafka

Producer

```
profile_updated
```

Consumers

- Recommendation Service
- Feed Service

---

## Redis

```
user:profile:{username}
```

TTL

```
30 Minutes
```

Automatically invalidated after updates.

---

## Storage

Bucket

```
profiles
```

Paths

```
avatars/{userId}.jpg

covers/{userId}.jpg
```

---

## Validation

- Username regex: `^[a-zA-Z0-9_]{3,30}$`
- 409 Conflict for duplicate usernames

---

# 12. Caching Strategy

OntDekker uses a layered caching approach.

| Cache | TTL | Purpose |
|--------|-----|----------|
| Personalized Feed | 5 min | Story ordering |
| Community Details | 15 min | Metadata & counts |
| Guide Search | 10 min | Filtered guide results |
| User Profile | 30 min | Public profile data |

---

## Strategy

**Stale-While-Revalidate (SWR)**

```
Cache

↓

Immediate Render

↓

Background Refresh

↓

Cache Update

↓

UI Refresh
```

---

# 13. Kafka Event Architecture

Kafka decouples expensive background operations from user-facing requests.

---

## Common Producers

- Feed Service
- Community Service
- Expedition Service
- Guide Service
- Chat Service
- User Service

---

## Common Consumers

- Recommendation Service
- Notification Service
- User Service
- Guide Service
- Chat Service
- Feed Service

---

## Typical Events

- `story_interacted`
- `comment_added`
- `community_membership_changed`
- `expedition_completed`
- `guide_reconnection_requested`
- `message_sent`
- `profile_updated`

---

# 14. Object Storage Architecture

All media is stored in **MinIO** and delivered through the CDN.

| Bucket | Purpose |
|----------|---------|
| `stories` | Story images |
| `communities` | Community banners |
| `expeditions` | Trip galleries |
| `guides` | Certifications |
| `chat` | Attachments |
| `profiles` | Avatars & covers |

---

# 15. Validation & Error Handling

Every service enforces validation using **Pydantic** models.

---

## Validation Rules

- Comment length limits
- Unique community names
- Positive gear weights
- Guide review eligibility
- Rating range (1–5)
- Username format validation

---

## Standard Error Codes

| Code | Meaning |
|------|----------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Resource Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

# 16. Complete Request Lifecycle

The following sequence illustrates how a typical frontend action propagates through the distributed system.

```
Client Application
        │
        ▼
Traefik API Gateway
        │
        ▼
Target Microservice
        │
        ▼
Database Transaction
        │
        ▼
HTTP Success Response
        │
        ▼
Kafka Event Published
        │
        ▼
Background Consumers
        ├── Recommendation Service
        ├── Notification Service
        ├── User Service
        └── Other Domain Services
```

---

# Integration Principles

OntDekker's frontend–backend integration is designed around **domain-driven microservices**, **event-driven communication**, and **clear ownership of data**. Synchronous REST APIs ensure immediate consistency for user actions, while Kafka-powered asynchronous workflows handle recommendations, notifications, analytics, and reputation updates without blocking the user experience. Combined with Redis caching, MinIO object storage, and standardized validation, this architecture provides a scalable, resilient, and production-ready foundation for the platform.