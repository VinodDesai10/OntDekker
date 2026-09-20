# OntDekker System Architecture

Version: 1.0

Status: Final

---

# Purpose

This document defines the complete high-level architecture of the OntDekker platform.

It acts as the single source of truth for how the entire backend is organized and how every service interacts.

All future implementation, documentation, APIs, deployment, and scaling strategies must conform to this architecture.

---

# Architecture Style

OntDekker follows a **Microservices Architecture**.

Each business domain is implemented as an independent microservice.

Every microservice:

- owns its own database
- owns its own business logic
- can be developed independently
- can be deployed independently
- communicates through APIs or events
- never directly accesses another service's database

---

# Why Microservices?

The platform consists of multiple independent business domains.

Examples

- Authentication
- User Profiles
- Stories
- Communities
- Expeditions
- Guides
- Chat
- Recommendations
- Notifications

These domains evolve independently.

Microservices allow:

- independent deployment
- better scalability
- fault isolation
- team ownership
- technology flexibility
- easier maintenance

---

# High Level Architecture

```
                        Users

                          │

                          ▼

                 Next.js Frontend

                          │

                  HTTPS / WebSocket

                          │

                          ▼

                 Traefik API Gateway

                          │

────────────────────────────────────────────────────────────

        Authentication Service

        User Service

        Feed Service

        Community Service

        Expedition Service

        Guide Service

        Recommendation Service

        Chat Service

        Notification Service

        Moderation Service

────────────────────────────────────────────────────────────

                 PostgreSQL Databases

(Database Per Service)

────────────────────────────────────────────────────────────

          Redis

          Kafka

          MinIO

────────────────────────────────────────────────────────────
```

---

# Layers

The architecture consists of five logical layers.

---

## Layer 1

Client Layer

Responsibilities

- UI
- User Interaction
- Routing
- Authentication State

Technology

- Next.js
- React
- TypeScript

---

## Layer 2

Gateway Layer

Responsibilities

- Route Requests
- Authentication Middleware
- Reverse Proxy
- Rate Limiting
- Load Balancing

Technology

Traefik

---

## Layer 3

Business Layer

Contains all microservices.

Each service owns

- business logic
- validation
- APIs
- database

---

## Layer 4

Infrastructure Layer

Contains

Redis

Kafka

MinIO

---

## Layer 5

Persistence Layer

Every service owns

- PostgreSQL database
- Alembic migrations
- SQLAlchemy models

---

# Microservice Boundaries

Authentication

↓

Authentication only

Never stores profile information.

---

User

↓

User profiles only.

Never authenticates users.

---

Feed

↓

Stories

Likes

Comments

Bookmarks

Shares

Media References

Does NOT recommend content.

---

Community

↓

Communities

Members

Rules

Discussions

Moderators

---

Expedition

↓

Expeditions

Participants

Reviews

Packing Lists

Gear Planner

Gallery

---

Guide

↓

Guide Applications

Verification

Guide Profiles

Travel Connections

---

Recommendation

↓

Personalization

Ranking

Suggestions

Interest Scoring

---

Notification

↓

Notification generation only.

Never creates content.

---

Chat

↓

Real-time messaging only.

---

Moderation

↓

Reports

Warnings

Audit

Suspensions

---

# Database Ownership

Every service owns its own PostgreSQL database.

```
Authentication

↓

auth_db

---------------------

User

↓

user_db

---------------------

Feed

↓

feed_db

---------------------

Community

↓

community_db

---------------------

Expedition

↓

trip_db

---------------------

Guide

↓

guide_db

---------------------

Recommendation

↓

recommendation_db

---------------------

Chat

↓

chat_db

---------------------

Notification

↓

notification_db

---------------------

Moderation

↓

moderation_db
```

Cross-database queries are prohibited.

---

# Service Communication

Two communication mechanisms are used.

---

## Synchronous

REST APIs

Used for

- CRUD
- Authentication
- Profile Lookup
- Community Details
- Expedition Details

Characteristics

- Immediate response
- Request/Response
- HTTP

---

## Asynchronous

Apache Kafka

Used only for events.

Examples

Story Created

↓

Recommendation Update

↓

Notification

↓

Analytics

↓

Reputation

Characteristics

- Non-blocking
- Eventually consistent
- Publish/Subscribe

---

# API Gateway Flow

```
Browser

↓

Traefik

↓

Route

↓

Target Service

↓

Service Database

↓

Response

↓

Browser
```

Gateway Responsibilities

- Routing
- SSL
- Compression
- Authentication Middleware
- Logging
- Request Forwarding

Business logic never belongs in the gateway.

---

# Event Driven Flow

Example

User likes a story.

```
User

↓

Feed Service

↓

Story Like Saved

↓

Publish STORY_LIKED Event

↓

Kafka

↓

Recommendation Service

↓

Notification Service

↓

Analytics
```

The Feed Service never waits for downstream services.

---

# Object Storage Flow

Images are never stored in PostgreSQL.

Flow

```
User Uploads Image

↓

MinIO

↓

Object URL Returned

↓

Feed Service

↓

Store URL inside PostgreSQL
```

---

# Redis Usage

Redis is NOT the primary database.

Redis stores

- Recommendation Cache
- Trending Stories
- Frequently Accessed Communities
- JWT Blacklist
- Session Cache

Redis data can always be regenerated.

---

# Service Independence

Each service can

- start independently
- stop independently
- deploy independently
- fail independently

Example

If Chat Service crashes

Authentication

Community

Stories

Expeditions

continue working normally.

---

# Scalability

Every service scales independently.

Example

Heavy story traffic

↓

Scale Feed Service

Heavy messaging

↓

Scale Chat Service

Heavy recommendations

↓

Scale Recommendation Service

---

# Fault Isolation

Failure in one service must never crash another.

If Recommendation Service fails

↓

Feed still loads

↓

Stories still work

↓

Only personalized ordering is unavailable.

---

# Domain Driven Design

Every service represents one business domain.

Authentication

↓

Identity

Community

↓

Social Groups

Feed

↓

Travel Stories

Expedition

↓

Collaborative Travel

Guide

↓

Local Experts

Recommendation

↓

Personalization

---

# Security

Authentication handled only by Authentication Service.

JWT is validated by downstream services.

Passwords are never stored in plaintext.

Every request requiring authentication includes

Authorization

Bearer Token

---

# Clean Architecture

Every microservice follows

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

Business rules remain inside the Domain layer.

---

# Service Dependencies

Authentication

↓

Independent

User

↓

Authentication

Feed

↓

Authentication

↓

User

Community

↓

Authentication

↓

User

Expedition

↓

Community

↓

Authentication

Guide

↓

Authentication

Recommendation

↓

Kafka Events

Notification

↓

Kafka Events

Chat

↓

Authentication

Moderation

↓

Authentication

Dependencies must remain minimal.

---

# Observability

Every service provides

- Health Check
- Metrics
- Structured Logs
- OpenAPI Documentation

Monitoring

Prometheus

Visualization

Grafana

Logs

Loki

---

# Deployment Strategy

Every service has

- Dockerfile
- Environment Variables
- Independent Build
- Independent Version

Deployment is container-based.

---

# Guiding Principles

The architecture must always satisfy the following principles.

- Database per service.
- Loose coupling.
- High cohesion.
- REST for synchronous communication.
- Kafka for asynchronous communication.
- Independent deployment.
- Horizontal scalability.
- Event-driven integration.
- Domain ownership.
- Clean Architecture.
- SOLID principles.
- API-first design.
- Infrastructure as reusable shared components.

---

# Summary

OntDekker is built as a modern distributed system where every business capability is implemented as an independent microservice.

The combination of FastAPI, PostgreSQL, Kafka, Redis, MinIO, and Traefik provides a scalable, maintainable, and production-ready foundation that supports future growth without requiring major architectural redesigns.