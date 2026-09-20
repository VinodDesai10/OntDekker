# 06 - Database Architecture

# OntDekker Database Architecture

Version: 1.0

Status: Final

---

# Overview

This document defines the database architecture for the OntDekker platform.

OntDekker follows the **Database per Service** pattern.

Every microservice owns exactly one PostgreSQL database.

No service is allowed to directly access another service's database.

This is one of the most important architectural principles of the platform.

---

# Database Philosophy

The database architecture follows the following principles.

- Database Per Service
- Domain Ownership
- Strong Consistency Within Service
- Eventual Consistency Across Services
- Loose Coupling
- Independent Deployment
- Independent Scaling

---

# Why Database Per Service?

Instead of one large database shared across all services, every service owns its own data.

Example

Authentication

↓

auth_db

User

↓

user_db

Feed

↓

feed_db

Community

↓

community_db

Expedition

↓

trip_db

Guide

↓

guide_db

Recommendation

↓

recommendation_db

Chat

↓

chat_db

Notification

↓

notification_db

Moderation

↓

moderation_db

---

# Benefits

✔ Independent schema evolution

✔ Independent deployment

✔ Independent scaling

✔ Better security

✔ Fault isolation

✔ Easier maintenance

✔ Domain ownership

---

# Why Not Shared Database?

Shared databases introduce

- Tight coupling
- Schema conflicts
- Difficult deployments
- Cross-service joins
- Lock contention
- Reduced scalability

OntDekker intentionally avoids this.

---

# Database Ownership

Every service is responsible for

- Tables
- Indexes
- Constraints
- Migrations
- Transactions
- Data Integrity

Only the owning service may modify its schema.

---

# Database Technology

Primary Database

PostgreSQL

Reasons

- ACID Compliance
- Mature Ecosystem
- JSON Support
- Full Text Search
- Excellent Indexing
- Open Source

---

# Database Naming

Every service has its own database.

```
auth_db

user_db

feed_db

community_db

trip_db

guide_db

recommendation_db

chat_db

notification_db

moderation_db
```

---

# Table Naming Convention

Use

snake_case

Examples

```
user_profiles

story_media

community_members

join_requests

guide_reviews

notification_preferences
```

Avoid

CamelCase

PascalCase

Plural inconsistency

---

# Primary Keys

Every table uses

UUID

Example

```
id UUID PRIMARY KEY
```

Reasons

- Globally unique

- Distributed friendly

- Easy merging

- Secure identifiers

Never expose sequential integers publicly.

---

# Foreign Keys

Within a service

↓

Normal PostgreSQL foreign keys.

Example

Story

↓

Story Media

Story

↓

Comments

Community

↓

Members

---

Across services

NO foreign keys.

Instead

Store reference IDs.

Example

Feed Service

```
author_id

community_id
```

These reference

User Service

Community Service

but are NOT PostgreSQL foreign keys.

Validation happens through APIs.

---

# Example

Feed Database

```
stories

id

author_id

community_id
```

author_id references

User Service

community_id references

Community Service

No SQL JOIN is allowed.

---

# Cross-Service Data

Never query another database.

Correct

```
Feed Service

↓

User Service API

↓

Profile
```

Wrong

```
Feed DB

JOIN

User DB
```

---

# Transactions

Transactions remain inside one service.

Never create distributed database transactions.

Instead

Use

Event Driven Architecture.

---

# Example

Correct

```
Insert Story

↓

Commit

↓

Publish Kafka Event
```

Never

```
Insert Story

↓

Insert Notification

↓

Insert Recommendation

↓

Single Transaction
```

---

# Eventual Consistency

Because every service owns its own database,

cross-service consistency is achieved using Kafka.

Example

Story Created

↓

Feed DB updated

↓

Kafka Event

↓

Recommendation updated

↓

Notification generated

Eventually consistent.

---

# Soft Deletes

Most business entities use

Soft Delete.

Fields

```
is_deleted

deleted_at

deleted_by
```

Examples

Stories

Communities

Expeditions

Profiles

Reasons

- Recovery

- Auditing

- Moderation

---

# Hard Deletes

Reserved for

Temporary Tokens

Expired Sessions

Cache Tables

Old Logs

---

# Audit Fields

Every important table contains

```
created_at

updated_at

created_by

updated_by
```

Optional

```
deleted_at

deleted_by
```

---

# Time Standard

Always store

UTC

Example

```
2026-07-16T12:30:45Z
```

Frontend converts to local timezone.

---

# Indexing Strategy

Primary Key

↓

Automatic Index

Additional indexes

Frequently searched fields

Examples

```
email

username

community_id

story_id

user_id

created_at

status
```

Composite indexes

Example

```
(user_id, created_at)
```

---

# Unique Constraints

Examples

Email

Username

Community Slug

Guide Verification Number

Use database constraints whenever uniqueness is required.

---

# Text Search

Use PostgreSQL Full Text Search where appropriate.

Examples

Stories

Communities

Guides

Future enhancements may introduce Elasticsearch if search complexity increases.

---

# JSON Columns

Use PostgreSQL JSONB only for flexible metadata.

Examples

Settings

Feature Flags

Preferences

Avoid storing core business entities in JSON.

---

# Large Files

Never store binary files inside PostgreSQL.

Store in

MinIO

Database stores

```
image_url

document_url
```

---

# Migrations

Tool

Alembic

Every schema change requires

New Migration

Never manually modify production schemas.

Migration Flow

```
Model Change

↓

Alembic Revision

↓

Review

↓

Apply

↓

Deploy
```

---

# Backup Strategy

Daily Full Backup

Hourly Incremental Backup

Point-in-Time Recovery enabled.

---

# Recovery Strategy

Backups verified regularly.

Restore tests performed periodically.

---

# Read Pattern

Application

↓

Repository

↓

SQLAlchemy

↓

PostgreSQL

Never bypass repositories.

---

# Write Pattern

Request

↓

Validation

↓

Service Layer

↓

Repository

↓

Transaction

↓

Commit

↓

Publish Event

---

# Performance Guidelines

Avoid

SELECT *

Use pagination.

Limit result sizes.

Index frequently filtered columns.

Avoid N+1 queries.

Use lazy/eager loading appropriately.

Cache expensive reads in Redis.

---

# Connection Pooling

Use SQLAlchemy connection pools.

Recommended

```
Pool Size

10–20

Overflow

20
```

Tune based on service load.

---

# Security

Use parameterized queries.

Never build SQL strings manually.

Encrypt database connections using TLS in production.

Restrict database credentials per service.

Each service has its own database user.

---

# Monitoring

Monitor

- Query latency
- Slow queries
- Connection count
- Deadlocks
- Index usage
- Disk growth

Prometheus collects metrics.

Grafana visualizes dashboards.

---

# Future Enhancements

Phase 2

- Read Replicas for Feed Service
- Query Optimization
- Partition Large Tables

Phase 3

- Sharding (if required)
- Multi-region Replication
- Advanced Backup Automation
- Archival Strategy

---

# Best Practices

✔ One database per microservice

✔ UUID primary keys

✔ No cross-service foreign keys

✔ Use Kafka for consistency

✔ Store files in MinIO

✔ Soft delete business entities

✔ Version schema with Alembic

✔ Use indexes wisely

✔ Optimize for reads and writes

✔ Keep transactions local to a service

---

# Summary

The OntDekker database architecture follows modern distributed system principles by assigning complete ownership of data to each microservice.

PostgreSQL serves as the authoritative source of truth for structured data, while MinIO handles object storage and Kafka ensures eventual consistency across service boundaries.

This architecture enables independent development, deployment, scaling, and maintenance while preserving strong consistency within each service and loose coupling across the platform.