# 05 - Service Communication

# OntDekker Communication Architecture

Version: 1.0

Status: Final

---

# Overview

This document defines how microservices communicate throughout the OntDekker platform.

Communication is divided into two categories:

1. Synchronous Communication
2. Asynchronous Communication

Choosing the correct communication mechanism is critical for scalability, maintainability, and fault tolerance.

---

# Communication Philosophy

The communication architecture follows these principles.

- Loose Coupling
- High Cohesion
- Event Driven Architecture
- Domain Ownership
- Database Per Service
- No Shared Database
- Fail Independently
- Eventually Consistent

Every service owns its data.

No service may directly access another service's database.

---

# Communication Types

There are four communication mechanisms used throughout OntDekker.

| Type | Technology | Purpose |
|-------|------------|---------|
| REST API | FastAPI | Synchronous request-response |
| Kafka | Apache Kafka | Asynchronous events |
| Redis | Redis | Cache & temporary shared state |
| WebSockets | FastAPI WebSockets | Real-time communication |

---

# REST Communication

REST is used whenever an immediate response is required.

Examples

- Login
- Register
- Fetch Profile
- View Community
- View Expedition
- View Story
- Update Profile

REST should never be used for background processing.

---

## REST Flow

```
Client

↓

Traefik Gateway

↓

Target Service

↓

Own Database

↓

Response

↓

Client
```

---

## REST Principles

REST should be

Stateless

Idempotent

Versioned

Secure

Well documented

---

## REST Authentication

Every protected request contains

Authorization

Bearer JWT_TOKEN

Every service validates JWT before processing.

---

## REST Timeout

Recommended timeout

```
3–5 seconds
```

Long-running operations should be asynchronous.

---

# API Gateway

Technology

Traefik

Responsibilities

- Request Routing
- Reverse Proxy
- TLS Termination
- Middleware
- Authentication Forwarding
- Load Balancing

The gateway contains **no business logic**.

---

## Gateway Flow

```
Browser

↓

Traefik

↓

Route

↓

Microservice

↓

Database

↓

Response
```

---

# Kafka Communication

Kafka is used only for asynchronous workflows.

A service publishes an event and immediately continues processing.

It never waits for consumers.

---

## Why Kafka?

Without Kafka

```
Feed

↓

Recommendation

↓

Notification

↓

Analytics

↓

User waits
```

With Kafka

```
Feed

↓

Save Story

↓

Publish Event

↓

Return Response

↓

Kafka

↓

Consumers process independently
```

User receives a faster response.

---

# Event Driven Architecture

Every business event becomes a Kafka event.

Example

Story Created

↓

Kafka

↓

Recommendation Service

↓

Notification Service

↓

Analytics

↓

Future ML Pipeline

---

# Kafka Topics

Recommended Topics

```
user-events

story-events

community-events

expedition-events

guide-events

notification-events

recommendation-events

moderation-events

chat-events

system-events
```

---

# Example Event

Story Created

```json
{
  "event_id": "uuid",
  "event_type": "STORY_CREATED",
  "timestamp": "2026-07-16T10:30:00Z",
  "service": "feed-service",
  "payload": {
    "story_id": "123",
    "author_id": "456",
    "community_id": "789"
  }
}
```

---

# Event Naming Convention

Past tense.

Examples

```
USER_REGISTERED

PROFILE_UPDATED

COMMUNITY_CREATED

COMMUNITY_JOINED

STORY_CREATED

STORY_LIKED

EXPEDITION_CREATED

PARTICIPANT_JOINED

GUIDE_APPROVED

MESSAGE_SENT

REPORT_CREATED
```

---

# Kafka Producers

Authentication

Publishes

```
USER_REGISTERED

USER_LOGGED_IN

PASSWORD_RESET
```

---

User

Publishes

```
PROFILE_UPDATED

USER_FOLLOWED

BADGE_EARNED
```

---

Feed

Publishes

```
STORY_CREATED

STORY_UPDATED

COMMENT_CREATED

STORY_LIKED
```

---

Community

Publishes

```
COMMUNITY_CREATED

COMMUNITY_JOINED

DISCUSSION_CREATED
```

---

Expedition

Publishes

```
EXPEDITION_CREATED

PARTICIPANT_JOINED

REVIEW_SUBMITTED
```

---

Guide

Publishes

```
GUIDE_APPROVED

GUIDE_REVIEWED
```

---

Chat

Publishes

```
MESSAGE_SENT
```

---

Moderation

Publishes

```
REPORT_CREATED

USER_SUSPENDED

USER_BANNED
```

---

# Kafka Consumers

Recommendation Service

Consumes

```
Stories

Communities

Expeditions

Guides

Profiles
```

---

Notification Service

Consumes

Almost every event.

---

Analytics (Future)

Consumes

Everything.

---

# Event Lifecycle

```
Business Action

↓

Database Commit

↓

Publish Kafka Event

↓

Kafka Topic

↓

Consumer

↓

Process

↓

Update Database

↓

Complete
```

---

# Transaction Strategy

Use

Database First

Event Second

Example

```
Insert Story

↓

Commit

↓

Publish STORY_CREATED
```

Never publish events before the database transaction succeeds.

---

# Event Ordering

Ordering is guaranteed within a Kafka partition.

Design consumers to tolerate delayed events.

---

# Event Idempotency

Consumers must safely process duplicate events.

Every event contains

```
event_id
```

Duplicate event?

↓

Ignore

---

# Dead Letter Queue

Failed events should be moved to

```
<topic>.DLQ
```

Example

```
story-events.DLQ
```

Allows later investigation.

---

# Retry Strategy

Transient Failure

↓

Retry

Recommended

```
3 retries

Exponential Backoff
```

Permanent Failure

↓

Dead Letter Queue

---

# Event Versioning

Every event should include

```
event_version
```

Example

```json
{
  "event_version": 1
}
```

Future schema changes remain backward compatible.

---

# Redis Communication

Redis is never used for permanent communication.

Used only for

- Cache
- Online Presence
- Recommendation Cache
- JWT Blacklist
- Session Data

---

# Cache Flow

```
Client

↓

API

↓

Redis

↓

Hit?

↓

Yes

↓

Return

↓

No

↓

Database

↓

Redis

↓

Client
```

---

# Cache Invalidation

Whenever data changes

↓

Update Database

↓

Invalidate Redis

↓

Next request rebuilds cache

---

# WebSocket Communication

Technology

FastAPI WebSockets

Used only by Chat Service.

---

# WebSocket Flow

```
Client

↓

WebSocket

↓

Chat Service

↓

Persist Message

↓

Broadcast

↓

Recipients
```

---

# Communication Matrix

| From | To | Type |
|------|----|------|
| Frontend | API Gateway | REST |
| Gateway | Services | REST |
| Feed | Recommendation | Kafka |
| Feed | Notification | Kafka |
| Community | Notification | Kafka |
| Expedition | Notification | Kafka |
| Guide | Recommendation | Kafka |
| Chat | Clients | WebSocket |
| Services | Redis | Cache |

---

# Failure Handling

REST Failure

↓

Return Error

Retry if appropriate

---

Kafka Failure

↓

Retry

↓

Dead Letter Queue

---

Redis Failure

↓

Fallback to Database

---

WebSocket Failure

↓

Reconnect Automatically

---

# Circuit Breaker (Future)

For inter-service REST calls.

If service unavailable

↓

Open Circuit

↓

Fail Fast

↓

Retry Later

---

# Observability

Every request should include

```
X-Request-ID
```

Every Kafka event should include

```
event_id

correlation_id
```

Allows tracing across services.

---

# Security

REST

JWT

HTTPS

Role Validation

---

Kafka

Private Network

Authenticated Brokers

---

Redis

Private Access

No Public Exposure

---

# Best Practices

✔ Prefer REST for immediate responses

✔ Prefer Kafka for background processing

✔ Never access another service's database

✔ Keep events immutable

✔ Make consumers idempotent

✔ Use retries with exponential backoff

✔ Version event payloads

✔ Cache only derived or frequently accessed data

✔ Keep WebSockets isolated to the Chat Service

✔ Design for eventual consistency

---

# Summary

OntDekker's communication architecture combines synchronous REST APIs, asynchronous Kafka events, Redis caching, and WebSocket-based real-time messaging to create a loosely coupled, highly scalable distributed system.

This design allows each microservice to evolve, scale, and fail independently while maintaining consistent user experiences and supporting future growth into a production-scale platform.