# OntDekker Backend Engineering Guide

## Overview

OntDekker is a production-grade community-driven travel social platform built using a distributed Microservices Architecture.

The backend is designed around domain-driven services that are independently deployable, loosely coupled, and horizontally scalable.

OntDekker is **NOT** a travel booking platform.

The backend focuses on enabling:

- Community-driven travel
- Travel stories
- Expeditions
- Verified local guides
- Personalized recommendations
- Real-time communication
- Reputation and trust

---

# Backend Philosophy

The backend follows these principles:

- Microservices Architecture
- Domain Driven Design (DDD)
- Database per Service
- Clean Architecture
- SOLID Principles
- API First Design
- Event Driven Architecture
- Independent Deployment
- High Cohesion
- Low Coupling

Each service owns its own business logic and database.

No service directly accesses another service's database.

---

# Technology Stack

## Programming Language

Python 3.12

---

## Web Framework

FastAPI

Reasons

- High Performance
- Native async support
- Automatic OpenAPI generation
- Excellent typing support
- Production ready

---

## ORM

SQLAlchemy 2.0

Reasons

- Mature ORM
- Strong typing
- Async support
- Flexible relationships
- Production grade

---

## Database Migrations

Alembic

Responsibilities

- Schema versioning
- Database migrations
- Rollbacks

---

## Validation

Pydantic v2

Responsibilities

- Request validation
- Response serialization
- Configuration management

---

## Authentication

JWT

python-jose

Password hashing

Passlib (bcrypt)

Supports

- Access Tokens
- Refresh Tokens
- Role Based Authorization

---

## Database

PostgreSQL

Every microservice owns an independent PostgreSQL database.

---

## API Gateway

Traefik

Responsibilities

- Reverse Proxy
- Routing
- SSL Termination
- Middleware
- Load Balancing

---

## Object Storage

MinIO

Stores

- Story Images
- Community Banners
- Profile Pictures
- Guide Documents
- Expedition Galleries

Only object URLs are stored in PostgreSQL.

---

## Event Streaming

Apache Kafka

Used only for asynchronous communication.

Examples

Story Created

↓

Recommendation Updated

↓

Notification Generated

↓

Analytics Updated

REST APIs remain the primary communication mechanism.

---

## Cache

Redis

Used for

- Recommendation Cache
- Trending Stories
- Frequently Accessed Data
- JWT Blacklist

Redis is never the source of truth.

---

## Real-Time Communication

WebSockets

Used for

- Private Chat
- Community Chat
- Expedition Chat

---

## API Documentation

OpenAPI

Swagger UI

Generated automatically by FastAPI.

---

## Monitoring

Prometheus

Grafana

---

## Logging

Grafana Loki

Structured logging is used across all services.

---

## Containerization

Docker

Docker Compose

Each microservice is containerized independently.

---

## CI/CD

GitHub Actions

Supports

- Testing
- Linting
- Image Builds
- Deployments

---

# High-Level Architecture

Client

↓

Next.js Frontend

↓

Traefik Gateway

↓

Target Microservice

↓

Own PostgreSQL Database

↓

If asynchronous event occurs

↓

Apache Kafka

↓

Interested Services consume event

↓

Recommendation

Notification

Analytics

Reputation

---

# Backend Goals

The backend should provide

- Scalability
- Reliability
- Maintainability
- Independent deployments
- Easy testing
- Clear ownership
- Fault isolation
- Extensibility

Every engineering decision should support these goals.