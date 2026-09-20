# 07 - Project Structure

# OntDekker Project Structure & Repository Standards

Version: 1.0

Status: Final

---

# Overview

This document defines the official repository structure for the OntDekker platform.

Every developer must follow this structure.

Every new microservice, shared package, and frontend module should conform to these standards.

The goals are

- Consistency
- Scalability
- Maintainability
- Easy onboarding
- Clear ownership
- Independent deployments

---

# Monorepo Philosophy

OntDekker uses a **Monorepo Architecture**.

All services are stored inside a single Git repository.

Benefits

- Easier dependency management
- Atomic commits
- Shared documentation
- Shared CI/CD
- Easier onboarding
- Unified version control

---

# Repository Structure

```
ontdekker/

├── apps/
│   ├── web/
│   └── admin/                    (Future)
│
├── services/
│   ├── authentication-service/
│   ├── user-service/
│   ├── feed-service/
│   ├── community-service/
│   ├── expedition-service/
│   ├── guide-service/
│   ├── recommendation-service/
│   ├── chat-service/
│   ├── notification-service/
│   └── moderation-service/
│
├── platform/
│   ├── gateway/
│   ├── monitoring/
│   └── observability/
│
├── infrastructure/
│   ├── docker/
│   ├── kafka/
│   ├── postgres/
│   ├── redis/
│   ├── traefik/
│   ├── minio/
│   └── monitoring/
│
├── shared/
│   ├── schemas/
│   ├── events/
│   ├── constants/
│   ├── utils/
│   └── typing/
│
├── docs/
│
├── scripts/
│
├── .github/
│
├── docker-compose.yml
├── Makefile
├── README.md
└── .env.example
```

---

# Apps Directory

Contains frontend applications.

```
apps/

web/

admin/ (future)
```

The frontend communicates with backend services only through the API Gateway.

---

# Services Directory

Contains all backend microservices.

Every service is completely independent.

Example

```
services/

authentication-service/

user-service/

feed-service/

...
```

Every service contains

- API
- Database
- Business Logic
- Dockerfile
- Tests

---

# Standard Service Structure

Every microservice must follow the same layout.

```
authentication-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

security/

middleware/

dependencies/

events/

workers/

tests/

alembic/

Dockerfile

requirements.txt

README.md

.env.example
```

---

# app/

Contains application source code.

Nothing outside app should contain Python source files.

---

# api/

Contains

FastAPI routers.

Example

```
auth.py

users.py

profiles.py
```

Only

- request parsing
- validation
- response formatting

Business logic must not exist here.

---

# core/

Contains

Application startup.

Examples

```
main.py

lifespan.py

logging.py
```

---

# config/

Contains

Application configuration.

Examples

```
settings.py

constants.py

feature_flags.py
```

Uses

Pydantic Settings.

---

# database/

Contains

SQLAlchemy setup.

Examples

```
engine.py

session.py

base.py
```

---

# models/

Contains

SQLAlchemy ORM models.

Only database models.

---

# repositories/

Responsible for

Database access.

Contains

CRUD operations.

Repositories never contain business logic.

---

# schemas/

Contains

Pydantic models.

Examples

```
CreateUserRequest

LoginRequest

ProfileResponse
```

Used for

Request

Response

Validation

Serialization

---

# services/

Contains

Business logic.

This is the heart of every microservice.

Example

```
AuthenticationService

UserService

FeedService
```

Repositories are called from here.

---

# security/

Authentication

Authorization

JWT

Password hashing

Only exists in services requiring security.

---

# middleware/

Examples

Logging

Authentication

Rate Limiting

Request ID

---

# dependencies/

FastAPI dependency injection.

Examples

```
Current User

Database Session

Settings
```

---

# events/

Kafka

Publishers

Consumers

Event handlers

---

# workers/

Background jobs.

Examples

Recommendation workers

Notification workers

Cleanup jobs

---

# tests/

Contains

Unit Tests

Integration Tests

API Tests

Suggested structure

```
tests/

unit/

integration/

fixtures/

conftest.py
```

---

# alembic/

Contains

Database migrations.

Never manually edit production schemas.

---

# Shared Directory

Contains reusable code.

```
shared/

schemas/

events/

constants/

utils/

typing/
```

Rules

No business logic.

Only reusable abstractions.

---

# Shared Schemas

Examples

```
Pagination

API Response

Error Response
```

---

# Shared Events

Contains Kafka event contracts.

Example

```
StoryCreated

UserRegistered

CommunityJoined
```

All services should import shared event definitions.

---

# Shared Constants

Examples

```
Roles

Permissions

Statuses

Topic Names
```

Avoid hardcoding values.

---

# Shared Utils

Contains

Generic utilities.

Examples

```
Date helpers

UUID generators

Retry utilities

Hash helpers
```

Must remain framework-independent.

---

# Infrastructure Directory

Contains infrastructure configuration only.

```
docker/

traefik/

redis/

postgres/

kafka/

minio/

monitoring/
```

No business code.

---

# Platform Directory

Contains platform-wide components.

Examples

Gateway

Monitoring

Observability

---

# Documentation Directory

```
docs/

backend/

frontend/

api/

architecture/

deployment/
```

Every architectural decision must be documented.

---

# Scripts Directory

Automation scripts.

Examples

```
setup.sh

reset-db.sh

seed.py

generate-openapi.py
```

---

# GitHub Directory

Contains

CI/CD

Issue templates

PR templates

Workflows

---

# Naming Conventions

Directories

snake_case

Python Files

snake_case.py

Classes

PascalCase

Functions

snake_case

Variables

snake_case

Constants

UPPER_CASE

Private methods

_prefix

---

# Import Order

Recommended

```
Standard Library

↓

Third Party

↓

Shared Package

↓

Local Imports
```

Use isort.

---

# Configuration

Every service contains

```
.env.example
```

Never commit

```
.env
```

---

# Docker

Every service owns

Dockerfile

The repository owns

docker-compose.yml

---

# Logging

Every service uses

Structured JSON logging.

Never print().

---

# API Documentation

Every service exposes

```
/docs

/redoc

/openapi.json
```

Generated automatically.

---

# Coding Standards

Follow

PEP 8

Type hints everywhere.

Async-first architecture.

Business logic belongs only in the service layer.

Repositories never call other services.

---

# Testing Standards

Every feature requires

- Unit Test
- Integration Test

Critical APIs should also have end-to-end tests.

---

# Dependency Rules

Allowed

```
API

↓

Services

↓

Repositories

↓

Database
```

Not Allowed

```
Repository

↓

API
```

Or

```
Repository

↓

Another Service
```

---

# Service Isolation

Every service owns

- Models
- Schemas
- Business Logic
- Database
- Events

No direct imports between services.

Communication occurs only through

- REST
- Kafka

---

# Documentation Standards

Every service includes

README.md

Containing

- Purpose
- Setup
- Environment Variables
- API Overview
- Running Instructions
- Testing Instructions

---

# Best Practices

✔ Keep services independent

✔ Keep shared package lightweight

✔ Never duplicate infrastructure code

✔ Use dependency injection

✔ Keep APIs thin

✔ Keep services thick

✔ Repository only for persistence

✔ Service only for business logic

✔ Document every architectural decision

---

# Summary

The OntDekker repository follows a structured monorepo architecture where each microservice is independently developed, tested, deployed, and maintained while sharing common infrastructure and reusable contracts.

A consistent project structure enables faster onboarding, cleaner code reviews, easier automation, and scalable long-term development. Every developer and AI coding assistant should follow this structure when adding or modifying functionality.