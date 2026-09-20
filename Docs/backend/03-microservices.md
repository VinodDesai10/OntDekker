# 03 - Microservices

# Part 1 — Authentication Service

Version: 1.0

Status: Final

---

# Overview

The Authentication Service is responsible for **Identity and Access Management (IAM)** across the OntDekker platform.

This service manages the complete authentication lifecycle of every user.

It is the **only** service allowed to:

- register users
- authenticate users
- generate JWT tokens
- issue refresh tokens
- verify emails
- reset passwords
- manage roles and permissions

No other microservice may implement authentication logic.

---

# Purpose

The purpose of this service is to provide secure authentication and authorization for the entire OntDekker ecosystem.

It establishes user identity and issues credentials used by all downstream services.

---

# Responsibilities

The Authentication Service owns the following business capabilities.

## User Registration

Supports:

- Email registration
- Password registration

Responsibilities

- validate email
- validate password strength
- prevent duplicate registration
- hash passwords
- generate verification token
- create user identity

---

## Login

Responsibilities

- verify credentials
- compare password hash
- generate access token
- generate refresh token
- return authenticated session

---

## JWT Authentication

Responsibilities

Generate

- Access Tokens
- Refresh Tokens

Validate

- JWT Signature
- Token Expiration
- Token Claims

---

## Refresh Token Management

Responsibilities

- issue refresh tokens
- rotate refresh tokens
- revoke refresh tokens
- blacklist invalid refresh tokens

---

## Email Verification

Responsibilities

- generate verification token
- verify email ownership
- activate account

---

## Password Reset

Responsibilities

- forgot password request
- generate reset token
- validate reset token
- update password

---

## Role Management

Supported roles

- USER
- GUIDE
- MODERATOR
- ADMIN

Role assignment belongs only to this service.

---

# Non Responsibilities

Authentication Service does NOT manage

- user profile
- interests
- reputation
- badges
- followers
- communities
- expeditions
- chat
- recommendations

These belong to other services.

---

# Database Ownership

Database

```
auth_db
```

Only Authentication Service may access this database.

---

# Database Tables

## users

Stores

- identity
- credentials
- verification status

Example

```
id

email

password_hash

is_verified

is_active

created_at

updated_at
```

---

## refresh_tokens

Stores

- refresh token
- expiration
- revocation

---

## roles

Stores

System roles.

```
USER

GUIDE

MODERATOR

ADMIN
```

---

## user_roles

Many-to-many relationship.

Supports future multiple roles.

---

## email_verification_tokens

Stores

- verification token
- expiration
- status

---

## password_reset_tokens

Stores

- reset token
- expiration
- usage status

---

# Public APIs

## POST

/auth/register

Creates new account.

---

## POST

/auth/login

Authenticates user.

Returns

- Access Token
- Refresh Token

---

## POST

/auth/refresh

Returns new access token.

---

## POST

/auth/logout

Revokes refresh token.

---

## GET

/auth/me

Returns authenticated user identity.

---

## POST

/auth/forgot-password

Generates reset token.

---

## POST

/auth/reset-password

Updates password.

---

## GET

/auth/verify-email

Marks email as verified.

---

# Internal APIs

Used only by trusted services.

Examples

```
Validate JWT

Get User Identity

Get User Roles
```

---

# Authentication Flow

```
Register

↓

Validate Email

↓

Hash Password

↓

Save User

↓

Generate Verification Token

↓

Return Success
```

---

Login Flow

```
Email

Password

↓

Validate Credentials

↓

Generate JWT

↓

Generate Refresh Token

↓

Save Refresh Token

↓

Return Tokens
```

---

Token Refresh Flow

```
Refresh Token

↓

Validate

↓

Generate New Access Token

↓

Return Access Token
```

---

Logout Flow

```
Logout

↓

Revoke Refresh Token

↓

Blacklist Token

↓

Success
```

---

# JWT Structure

JWT contains

```
sub

email

roles

iat

exp
```

Never store

- password
- profile
- reputation

inside JWT.

---

# Security

Passwords

↓

bcrypt hashing

Never reversible.

---

HTTPS only.

---

Refresh tokens stored securely.

---

Rate limit login attempts.

---

Prevent brute-force attacks.

---

Prevent duplicate registration.

---

Validate email format.

---

Strong password policy.

---

# Published Events

Authentication Service publishes Kafka events.

Examples

```
USER_REGISTERED

USER_LOGGED_IN

USER_VERIFIED

PASSWORD_RESET

ROLE_UPDATED
```

---

# Consumed Events

Authentication Service consumes almost no business events.

It remains largely independent.

---

# Dependencies

Infrastructure

- PostgreSQL
- Redis
- Traefik
- JWT
- Passlib

No dependency on business services.

---

# Scaling

Can scale independently.

High login traffic

↓

Scale Authentication Service only.

---

# Folder Structure

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
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

Business rules remain in Domain.

---

# Failure Scenarios

Database unavailable

↓

Return 503

---

Invalid credentials

↓

401 Unauthorized

---

Expired JWT

↓

401 Unauthorized

---

Expired refresh token

↓

Force login

---

Invalid verification token

↓

400 Bad Request

---

# Logging

Log

- successful login
- failed login
- registration
- password reset
- verification

Never log

- passwords
- tokens
- secrets

---

# Monitoring

Expose

```
/health

/metrics
```

Prometheus collects metrics.

---

# Docker

Authentication Service runs independently.

Environment variables

```
DATABASE_URL

JWT_SECRET

JWT_ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES

REFRESH_TOKEN_EXPIRE_DAYS

REDIS_URL

KAFKA_URL
```

---

# Future Enhancements

Phase 2

- OAuth
- Google Login
- GitHub Login

Phase 3

- Multi-factor Authentication
- Device Management
- Session Management
- Login History
- Risk-based Authentication

---

# Ownership Summary

Authentication Service owns

✔ Identity

✔ Credentials

✔ Tokens

✔ Roles

✔ Authentication

✔ Authorization

Authentication Service never owns

✖ Profiles

✖ Stories

✖ Communities

✖ Expeditions

✖ Guides

✖ Chat

✖ Recommendations

This strict ownership ensures a clean separation of concerns and allows the service to evolve independently while providing secure identity management across the OntDekker platform.


# Part 2 — User Service

Version: 1.0

Status: Final

---

# Overview

The User Service is responsible for managing all user profile information across the OntDekker platform.

While the Authentication Service manages **who the user is**, the User Service manages **who the user appears to be**.

This includes:

- Public Profile
- Private Profile
- Travel Interests
- Travel Preferences
- Followers
- Following
- Reputation
- Badges
- Travel Statistics

The User Service never authenticates users.

Authentication belongs exclusively to the Authentication Service.

---

# Purpose

Provide a centralized profile service that stores all user-related information except authentication.

The User Service acts as the social identity layer of OntDekker.

---

# Responsibilities

The User Service owns:

## User Profile

Stores

- Name
- Username
- Biography
- Profile Picture
- Cover Image
- Country
- City
- Languages

---

## Travel Preferences

Stores

- Preferred Travel Style
- Preferred Destinations
- Budget Preference
- Adventure Level
- Interests

Examples

- Trekking
- Backpacking
- Wildlife
- Heritage
- Photography
- Food
- Road Trips
- Camping

---

## Public Profile

Visible to everyone.

Contains

- Avatar
- Name
- Username
- Bio
- Reputation
- Followers
- Following
- Badges
- Communities Joined
- Expeditions Joined
- Travel Stories

---

## Private Profile

Visible only to owner.

Contains

- Email
- Preferences
- Notification Settings
- Saved Content
- Personal Information

---

## Followers

Supports

Follow User

Unfollow User

Followers List

Following List

Mutual Followers

Follower Count

---

## Reputation

Stores

Explorer Score

Trusted Traveler Score

Community Participation

Expeditions Joined

Expeditions Organized

Guide Interactions

Reviews Received

---

## Badges

Supports

Trusted Traveler

Community Builder

Expedition Leader

Verified Guide

Top Contributor

Explorer

Future badges can be added without schema changes.

---

## Saved Content

Stores references to

Saved Stories

Saved Communities

Saved Expeditions

Saved Guides

Only references are stored.

Original content remains in owning services.

---

# Responsibilities NOT Owned

User Service does NOT manage

Authentication

Passwords

JWT

Refresh Tokens

Communities

Stories

Expeditions

Guides

Messages

Notifications

---

# Database Ownership

Database

```
user_db
```

No other service may access this database.

---

# Database Tables

## user_profiles

Stores

User identity visible to platform.

Fields

```
id

auth_user_id

username

display_name

bio

avatar_url

cover_url

city

country

created_at

updated_at
```

---

## interests

Stores travel interests.

Example

```
user_id

interest

created_at
```

---

## preferences

Stores

Preferred

Travel Style

Budget

Languages

Notification Preferences

Privacy Preferences

---

## followers

Stores

```
follower_id

following_id

created_at
```

---

## badges

Stores

Awarded badges.

```
badge_name

badge_icon

earned_at
```

---

## reputation

Stores

Explorer Score

Travel Statistics

Community Score

Review Score

---

## saved_items

Stores

Reference IDs

Story

Community

Expedition

Guide

---

# Public APIs

## GET

/users/me

Returns own profile.

---

## PUT

/users/me

Update profile.

---

## GET

/users/{id}

Returns public profile.

---

## POST

/users/{id}/follow

Follow user.

---

## DELETE

/users/{id}/follow

Unfollow.

---

## GET

/users/{id}/followers

Followers list.

---

## GET

/users/{id}/following

Following list.

---

## GET

/users/{id}/badges

Returns earned badges.

---

## GET

/users/{id}/reputation

Returns reputation details.

---

## POST

/users/me/avatar

Upload avatar.

Returns object URL.

---

## POST

/users/me/cover

Upload cover image.

Returns object URL.

---

# Internal APIs

Used by trusted services.

Examples

```
Get Username

Get Avatar

Get Reputation

Get Public Profile
```

Authentication required.

---

# Profile Creation Flow

```
User Registers

↓

Authentication Service

↓

USER_REGISTERED Event

↓

User Service

↓

Create Empty Profile

↓

Return Success
```

---

# Follow Flow

```
User Clicks Follow

↓

Validate Target User

↓

Insert Follow Relationship

↓

Update Counts

↓

Publish USER_FOLLOWED Event
```

---

# Avatar Upload Flow

```
Upload Image

↓

MinIO

↓

Object URL

↓

Store URL in user_db

↓

Return URL
```

---

# Reputation

The User Service stores reputation.

Calculation logic may evolve.

Initial Metrics

Explorer Score

Stories Shared

Communities Joined

Expeditions Joined

Followers

Positive Reviews

Guide Interactions

Future AI-based scoring can replace rule-based logic.

---

# Badge System

Initial Badges

Trusted Traveler

Explorer

Community Builder

Verified Guide

Top Organizer

Badges are awarded by events.

---

# Kafka Events Published

```
PROFILE_UPDATED

USER_FOLLOWED

USER_UNFOLLOWED

BADGE_EARNED

PROFILE_PICTURE_UPDATED
```

---

# Kafka Events Consumed

```
USER_REGISTERED

EXPEDITION_COMPLETED

COMMUNITY_JOINED

GUIDE_VERIFIED

STORY_CREATED
```

These events update reputation and badges.

---

# Dependencies

Depends on

Authentication Service

MinIO

PostgreSQL

Redis

Kafka

Does NOT depend on

Feed

Community

Chat

Recommendation

---

# Scaling

Scale independently.

Heavy profile traffic

↓

Scale User Service.

Heavy follower traffic

↓

Scale User Service only.

---

# Folder Structure

```
user-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

dependencies/

events/

workers/

tests/

alembic/

Dockerfile

requirements.txt

README.md
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

Business rules remain inside Domain.

---

# Failure Scenarios

Profile not found

↓

404

---

Username already exists

↓

409

---

Avatar upload fails

↓

500

---

User follows themselves

↓

400

---

Invalid profile update

↓

422

---

# Logging

Log

Profile Created

Profile Updated

Avatar Changed

Follow

Unfollow

Badge Earned

Never log

Sensitive personal information.

---

# Monitoring

Expose

```
/health

/metrics
```

Metrics

Profile Updates

Followers

Badge Awards

Request Latency

---

# Docker

Runs independently.

Environment Variables

```
DATABASE_URL

MINIO_ENDPOINT

MINIO_ACCESS_KEY

MINIO_SECRET_KEY

REDIS_URL

KAFKA_URL

JWT_PUBLIC_KEY
```

---

# Future Enhancements

Phase 2

Travel Statistics Dashboard

Travel Journal

Visited Countries

Wishlist

Activity Timeline

---

Phase 3

Social Graph Analysis

AI Interest Profiling

Recommendation Signals

Travel Milestones

Privacy Controls

---

# Ownership Summary

User Service owns

✔ Public Profile

✔ Private Profile

✔ Followers

✔ Following

✔ Reputation

✔ Badges

✔ Interests

✔ Preferences

✔ Saved References

User Service never owns

✖ Authentication

✖ Passwords

✖ Stories

✖ Communities

✖ Expeditions

✖ Guides

✖ Chat

✖ Notifications

This strict ownership ensures that user identity and social profile management remain independent from authentication and other business domains, enabling clean service boundaries and easier scalability.


# Part 3 — Feed Service

Version: 1.0

Status: Final

---

# Overview

The Feed Service is responsible for managing all travel stories and social interactions within OntDekker.

Unlike traditional social media platforms, OntDekker emphasizes meaningful travel experiences rather than short-form content.

The Feed Service stores and manages travel stories, media references, comments, reactions, bookmarks, and shares.

This service **does not personalize or rank the feed**.

Feed ranking belongs exclusively to the Recommendation Service.

---

# Purpose

Provide a scalable social content platform where travelers can document, share, and engage with authentic travel experiences.

---

# Responsibilities

The Feed Service owns the following business capabilities.

## Travel Stories

Users can

- Create Story
- Edit Story
- Delete Story
- View Story
- Archive Story

Each story contains

- Title
- Caption
- Story Content
- Images
- Location
- Travel Tags
- Community Reference
- Expedition Reference (Optional)
- Visibility
- Creation Metadata

---

## Story Media

Supports

- Multiple Images
- Ordered Gallery
- Cover Image

Images are stored in MinIO.

Only object URLs are stored in PostgreSQL.

---

## Story Engagement

Supports

- Like
- Unlike
- Bookmark
- Remove Bookmark
- Share
- View Count

---

## Comments

Supports

- Add Comment
- Edit Comment
- Delete Comment
- Nested Replies
- Like Comment

---

## Story Discovery

Provides

Latest Stories

Community Stories

User Stories

Trending Stories

Personalized ranking is NOT performed here.

---

# Responsibilities NOT Owned

Feed Service never manages

Authentication

User Profiles

Communities

Expeditions

Recommendations

Notifications

Chat

Guides

Moderation Decisions

---

# Database Ownership

Database

```
feed_db
```

No other service may access this database directly.

---

# Database Tables

## stories

Stores

Travel stories.

Fields

```
id

author_id

community_id

expedition_id

title

content

location

visibility

created_at

updated_at

status
```

---

## story_media

Stores

Image references.

Fields

```
id

story_id

media_url

display_order

created_at
```

---

## story_tags

Stores

Travel tags.

Examples

```
Hiking

Camping

Food

Photography

Wildlife

Culture
```

---

## likes

Stores

Story likes.

Fields

```
story_id

user_id

created_at
```

---

## bookmarks

Stores

Saved stories.

Fields

```
story_id

user_id

created_at
```

---

## comments

Stores

Discussion.

Fields

```
id

story_id

author_id

parent_comment_id

content

created_at
```

Supports nested replies.

---

## shares

Stores

Share statistics.

---

## story_views

Stores

View analytics.

---

# Public APIs

## POST

/feed/stories

Create Story

---

## GET

/feed/stories

Latest Stories

---

## GET

/feed/stories/{id}

Story Details

---

## PUT

/feed/stories/{id}

Update Story

---

## DELETE

/feed/stories/{id}

Delete Story

---

## POST

/feed/stories/{id}/like

Like Story

---

## DELETE

/feed/stories/{id}/like

Unlike Story

---

## POST

/feed/stories/{id}/bookmark

Bookmark Story

---

## DELETE

/feed/stories/{id}/bookmark

Remove Bookmark

---

## POST

/feed/stories/{id}/comment

Create Comment

---

## PUT

/feed/comments/{id}

Update Comment

---

## DELETE

/feed/comments/{id}

Delete Comment

---

## POST

/feed/comments/{id}/reply

Reply to Comment

---

## POST

/feed/stories/{id}/share

Share Story

---

## GET

/feed/users/{user_id}

Stories by User

---

## GET

/feed/communities/{community_id}

Stories for Community

---

# Internal APIs

Provides

```
Get Story

Get Story Count

Get Recent Stories

Get Trending Stories

Validate Story Ownership
```

---

# Story Creation Flow

```
User

↓

Create Story

↓

Validate Input

↓

Upload Images to MinIO

↓

Store URLs

↓

Persist Story

↓

Publish STORY_CREATED Event

↓

Return Story
```

---

# Story Like Flow

```
User

↓

Like Story

↓

Insert Like

↓

Increment Like Count

↓

Publish STORY_LIKED Event
```

---

# Comment Flow

```
User

↓

Write Comment

↓

Validate

↓

Save Comment

↓

Publish COMMENT_CREATED Event
```

---

# Bookmark Flow

```
Bookmark

↓

Save Bookmark

↓

Return Success
```

Bookmarks are private.

---

# Share Flow

```
Share Story

↓

Increment Counter

↓

Generate Share Link

↓

Publish STORY_SHARED Event
```

---

# Story Lifecycle

Draft

↓

Published

↓

Edited

↓

Archived

↓

Deleted

Deleted stories remain recoverable for moderation until permanent cleanup.

---

# MinIO Integration

Flow

```
Image Upload

↓

MinIO

↓

Object URL

↓

Feed Service

↓

Store URL
```

The Feed Service never stores binary media inside PostgreSQL.

---

# Feed Retrieval

Feed Service returns

Chronological Stories

Community Stories

User Stories

Trending Stories

Personalization occurs later inside Recommendation Service.

---

# Kafka Events Published

```
STORY_CREATED

STORY_UPDATED

STORY_DELETED

STORY_LIKED

STORY_UNLIKED

COMMENT_CREATED

COMMENT_UPDATED

COMMENT_DELETED

STORY_BOOKMARKED

STORY_SHARED
```

---

# Kafka Events Consumed

```
USER_DELETED

COMMUNITY_DELETED

EXPEDITION_DELETED
```

Used to clean references.

---

# Dependencies

Depends on

Authentication Service

User Service

Community Service

MinIO

PostgreSQL

Kafka

Redis

Does NOT depend on

Recommendation

Notification

Chat

Guide

---

# Scaling

Feed Service is expected to receive the highest traffic.

Scale independently.

Example

Heavy Story Traffic

↓

Scale Feed Service only.

Media uploads can also be isolated behind dedicated workers in future.

---

# Folder Structure

```
feed-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

storage/

events/

workers/

dependencies/

tests/

alembic/

Dockerfile

requirements.txt

README.md
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

Business rules remain in Domain.

---

# Failure Scenarios

Story not found

↓

404

---

Unauthorized edit

↓

403

---

Image upload failed

↓

500

---

Comment too long

↓

422

---

Bookmark already exists

↓

409

---

# Logging

Log

Story Created

Story Updated

Story Deleted

Story Liked

Comment Created

Bookmark Created

Share Created

Never log

Story drafts

Private content

Secrets

---

# Monitoring

Expose

```
/health

/metrics
```

Metrics

Story Creation Rate

Like Rate

Comment Rate

Average Response Time

Media Upload Time

Error Rate

---

# Docker

Runs independently.

Environment Variables

```
DATABASE_URL

MINIO_ENDPOINT

MINIO_ACCESS_KEY

MINIO_SECRET_KEY

REDIS_URL

KAFKA_URL

JWT_PUBLIC_KEY
```

---

# Future Enhancements

Phase 2

- Rich Text Editor
- Story Drafts
- Story Version History
- Polls
- Story Reactions beyond Likes

Phase 3

- AI-assisted Story Formatting
- Automatic Image Compression
- Duplicate Media Detection
- Story Collections
- Story Translation

---

# Ownership Summary

Feed Service owns

✔ Travel Stories

✔ Story Media References

✔ Comments

✔ Likes

✔ Bookmarks

✔ Shares

✔ Story Views

Feed Service never owns

✖ Authentication

✖ User Profiles

✖ Communities

✖ Expeditions

✖ Recommendations

✖ Notifications

✖ Chat

✖ Guide Profiles

✖ Moderation Decisions

The Feed Service is responsible only for storing and serving social content. Feed personalization, recommendation ranking, notifications, and analytics are delegated to dedicated services, ensuring clear separation of concerns and allowing the platform to scale efficiently.



# Part 4 — Community Service

Version: 1.0

Status: Final

---

# Overview

The Community Service is the central domain of OntDekker.

Unlike traditional social media where posts are the primary entity, OntDekker revolves around communities.

Every meaningful social interaction begins within a community.

Communities organize:

- Travel Stories
- Expeditions
- Discussions
- Members
- Moderators
- Rules

This service owns the complete lifecycle of communities.

No other service may create or manage communities.

---

# Purpose

Provide a scalable platform for travelers to create, join, manage, and engage in travel-focused communities.

Communities are the primary organizational unit of OntDekker.

---

# Responsibilities

The Community Service owns the following business capabilities.

## Community Management

Supports

- Create Community
- Edit Community
- Archive Community
- Delete Community

Community Properties

- Name
- Slug
- Description
- Banner Image
- Profile Image
- Visibility
- Category
- Location (Optional)

---

## Community Membership

Supports

- Join Community
- Leave Community
- Join Requests (Private Communities)
- Member List
- Member Roles

Membership States

- Pending
- Member
- Moderator
- Owner
- Banned

---

## Moderators

Supports

- Promote Member
- Demote Moderator
- Remove Member
- Ban Member
- Invite Moderator

---

## Community Rules

Each community maintains its own rule set.

Examples

- Respect Local Culture
- No Spam
- No Commercial Promotion
- Stay On Topic

---

## Discussions

Supports

- Create Discussion
- Comment
- Pin Discussion
- Lock Discussion
- Delete Discussion

Discussions are independent from Travel Stories.

---

## Community Metadata

Stores

- Member Count
- Expedition Count
- Story Count
- Creation Date
- Community Status

---

# Responsibilities NOT Owned

Community Service never manages

Authentication

Stories

Story Comments

Expeditions

Chat

Recommendations

Notifications

Guide Verification

---

# Database Ownership

Database

```
community_db
```

Only Community Service may access this database.

---

# Database Tables

## communities

Stores

Community information.

Fields

```
id

name

slug

description

banner_url

logo_url

visibility

category

created_by

created_at

updated_at

status
```

---

## community_members

Stores

Membership.

```
community_id

user_id

role

joined_at

status
```

---

## community_rules

Stores

Community rules.

---

## discussions

Stores

Community discussions.

```
id

community_id

author_id

title

content

created_at
```

---

## discussion_comments

Stores

Replies.

---

## join_requests

Stores

Private community requests.

---

# Public APIs

## POST

/communities

Create Community

---

## GET

/communities

Browse Communities

---

## GET

/communities/{id}

Community Details

---

## PUT

/communities/{id}

Update Community

---

## DELETE

/communities/{id}

Archive Community

---

## POST

/communities/{id}/join

Join Community

---

## DELETE

/communities/{id}/leave

Leave Community

---

## GET

/communities/{id}/members

Member List

---

## GET

/communities/{id}/discussions

Community Discussions

---

## POST

/communities/{id}/discussions

Create Discussion

---

## POST

/discussions/{id}/comments

Comment on Discussion

---

## GET

/communities/{id}/rules

Community Rules

---

# Internal APIs

Provides

```
Validate Community

Get Member Count

Check Membership

Check Moderator Status

Get Community Metadata
```

---

# Community Creation Flow

```
User

↓

Create Community

↓

Validate Input

↓

Upload Banner

↓

Store Images

↓

Create Community

↓

Creator becomes Owner

↓

Publish COMMUNITY_CREATED

↓

Return Success
```

---

# Join Community Flow

Public Community

```
Join

↓

Become Member

↓

Publish COMMUNITY_JOINED
```

Private Community

```
Join

↓

Create Join Request

↓

Owner Approves

↓

Become Member
```

---

# Moderator Flow

```
Owner

↓

Promote Member

↓

Moderator Role Updated

↓

Publish MEMBER_PROMOTED
```

---

# Discussion Flow

```
Create Discussion

↓

Save

↓

Publish DISCUSSION_CREATED
```

---

# Community Lifecycle

```
Created

↓

Active

↓

Archived

↓

Deleted
```

Archived communities remain viewable.

Deleted communities are retained for moderation until cleanup.

---

# MinIO Integration

Stores

- Banner Image
- Logo Image

Only URLs are stored inside PostgreSQL.

---

# Kafka Events Published

```
COMMUNITY_CREATED

COMMUNITY_UPDATED

COMMUNITY_ARCHIVED

COMMUNITY_JOINED

COMMUNITY_LEFT

MEMBER_PROMOTED

MEMBER_REMOVED

DISCUSSION_CREATED

DISCUSSION_COMMENTED
```

---

# Kafka Events Consumed

```
USER_REGISTERED

USER_DELETED

EXPEDITION_CREATED

STORY_CREATED
```

Used to update metadata and clean references.

---

# Dependencies

Depends on

Authentication Service

User Service

MinIO

PostgreSQL

Kafka

Redis

Does NOT depend on

Feed

Recommendation

Notification

Chat

Guide

---

# Scaling

Community Service scales independently.

Heavy community traffic

↓

Scale Community Service only.

---

# Folder Structure

```
community-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

storage/

events/

workers/

dependencies/

tests/

alembic/

Dockerfile

requirements.txt

README.md
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

---

# Failure Scenarios

Community not found

↓

404

---

Already a member

↓

409

---

Private join request already pending

↓

409

---

Unauthorized moderator action

↓

403

---

Banner upload failed

↓

500

---

# Logging

Log

Community Created

Community Updated

Member Joined

Member Left

Discussion Created

Moderator Assigned

Never log

Private discussions

Sensitive moderation data

---

# Monitoring

Expose

```
/health

/metrics
```

Metrics

Community Creation Rate

Join Requests

Member Growth

Discussion Count

API Latency

---

# Docker

Runs independently.

Environment Variables

```
DATABASE_URL

MINIO_ENDPOINT

MINIO_ACCESS_KEY

MINIO_SECRET_KEY

REDIS_URL

KAFKA_URL

JWT_PUBLIC_KEY
```

---

# Future Enhancements

Phase 2

- Community Categories
- Featured Communities
- Community Analytics
- Community Invitations
- Community Events

Phase 3

- AI Community Recommendations
- Community Health Score
- Auto Moderator Suggestions
- Community Verification
- Community Insights Dashboard

---

# Ownership Summary

Community Service owns

✔ Community Lifecycle

✔ Members

✔ Membership

✔ Join Requests

✔ Moderators

✔ Rules

✔ Discussions

✔ Community Metadata

Community Service never owns

✖ Authentication

✖ User Profiles

✖ Travel Stories

✖ Expedition Details

✖ Chat

✖ Notifications

✖ Recommendation Logic

✖ Guide Profiles

The Community Service is the backbone of OntDekker. Every Expedition belongs to a Community, most Stories are associated with a Community, and Communities define the social structure of the platform. It remains focused solely on community management while delegating content, messaging, recommendations, and notifications to their respective services.


# Part 5 — Expedition Service

Version: 1.0

Status: Final

---

# Overview

The Expedition Service is responsible for managing the complete lifecycle of community-organized expeditions.

Unlike traditional travel applications, an expedition is **not** merely a trip listing.

An expedition is a collaborative workspace where members plan, discuss, prepare, participate, and preserve memories together.

Every expedition belongs to exactly one community.

An expedition cannot exist independently.

---

# Purpose

Provide a collaborative platform for community members to organize meaningful travel experiences.

The Expedition Service serves as the planning and execution hub for every community journey.

---

# Responsibilities

The Expedition Service owns the following business capabilities.

## Expedition Management

Supports

- Create Expedition
- Edit Expedition
- Cancel Expedition
- Archive Expedition
- Delete Expedition

Every expedition stores

- Community
- Organizer
- Destination
- Meeting Point
- Start Date
- End Date
- Budget
- Description
- Maximum Participants
- Status

---

## Participant Management

Supports

- Join Expedition
- Leave Expedition
- Accept Join Request
- Reject Join Request
- Remove Participant
- Participant List

Participant Roles

- Organizer
- Co-Organizer
- Participant

---

## Join Requests

Private approval workflow.

Supports

- Request to Join
- Approve
- Reject
- Cancel Request

---

## Expedition Overview

Displays

Destination

Community

Organizer

Budget

Dates

Difficulty

Participants

Status

Description

Cover Image

---

## Itinerary

Supports

Daily itinerary planning.

Each day contains

- Title
- Description
- Time
- Location
- Notes

---

## Expedition Discussion

Supports

- Messages
- Announcements
- Questions
- Polls (Future)

Separate from Community Discussions.

Only expedition participants may access.

---

## Expedition Gallery

Supports

- Upload Photos
- View Photos
- Delete Own Photos
- Expedition Memories

Media stored in MinIO.

---

## Gear Planner

One of OntDekker's signature features.

Supports

Base Pack

Consumables

Worn Gear

Custom Items

Each item stores

- Name
- Category
- Weight
- Quantity
- Packed Status

---

## Pack Weight Optimizer

Automatically calculates

Total Pack Weight

Weight Categories

Ultralight

Lightweight

Standard

Heavy

Displays

Progress Bar

Weight Breakdown

Category Summary

---

## Packing Checklist

Supports

Checkbox tracking.

Example

✔ Sleeping Bag

✔ Tent

✖ Stove

✔ Water Filter

---

## Reviews

After expedition completion

Participants can review

- Organizer
- Fellow Travelers
- Overall Experience

Review categories

Communication

Safety

Punctuality

Organization

Friendliness

Would Travel Again

These reviews contribute to User Reputation.

---

# Responsibilities NOT Owned

Expedition Service never manages

Authentication

Communities

Stories

Recommendations

Notifications

Chat Infrastructure

Guide Verification

Payments

---

# Database Ownership

Database

```
trip_db
```

Only Expedition Service accesses this database.

---

# Database Tables

## expeditions

Stores

```
id

community_id

organizer_id

title

destination

description

meeting_point

budget

start_date

end_date

max_participants

status

cover_image_url

created_at
```

---

## expedition_participants

Stores

```
expedition_id

user_id

role

joined_at

status
```

---

## join_requests

Stores

```
id

expedition_id

user_id

message

status

created_at
```

---

## itinerary

Stores

```
day_number

title

description

location

time
```

---

## expedition_gallery

Stores

Image URLs.

---

## gear_items

Stores

Packing items.

```
item_name

category

weight

quantity

packed
```

---

## reviews

Stores

Post-expedition reviews.

---

# Public APIs

## POST

/expeditions

Create Expedition

---

## GET

/expeditions

Browse Expeditions

---

## GET

/expeditions/{id}

Expedition Details

---

## PUT

/expeditions/{id}

Update Expedition

---

## DELETE

/expeditions/{id}

Cancel Expedition

---

## POST

/expeditions/{id}/join

Request Join

---

## POST

/expeditions/{id}/approve

Approve Participant

---

## POST

/expeditions/{id}/reject

Reject Participant

---

## DELETE

/expeditions/{id}/leave

Leave Expedition

---

## GET

/expeditions/{id}/participants

Participant List

---

## GET

/expeditions/{id}/itinerary

View Itinerary

---

## PUT

/expeditions/{id}/itinerary

Update Itinerary

---

## POST

/expeditions/{id}/gallery

Upload Photos

---

## POST

/expeditions/{id}/gear

Add Gear Item

---

## PUT

/expeditions/{id}/gear

Update Gear

---

## POST

/expeditions/{id}/review

Submit Review

---

# Internal APIs

Provides

```
Validate Expedition

Get Participants

Get Organizer

Get Expedition Metadata

Check Membership

Check Organizer
```

---

# Expedition Creation Flow

```
Organizer

↓

Select Community

↓

Enter Details

↓

Upload Cover Image

↓

Create Expedition

↓

Organizer becomes Participant

↓

Publish EXPEDITION_CREATED

↓

Return Success
```

---

# Join Flow

Public Expedition

```
Join

↓

Become Participant

↓

Publish PARTICIPANT_JOINED
```

Private Expedition

```
Join

↓

Join Request

↓

Organizer Reviews

↓

Approved

↓

Become Participant
```

---

# Gear Planner Flow

```
Open Packing Tab

↓

Add Gear

↓

Weight Calculated

↓

Category Updated

↓

Checklist Updated
```

---

# Gallery Flow

```
Upload Image

↓

MinIO

↓

Store URL

↓

Gallery Updated
```

---

# Review Flow

```
Expedition Completed

↓

Participant Opens Review

↓

Submit Review

↓

Publish REVIEW_SUBMITTED
```

---

# Expedition Lifecycle

```
Draft

↓

Published

↓

Open for Joining

↓

In Progress

↓

Completed

↓

Archived
```

---

# MinIO Integration

Stores

- Cover Images
- Gallery Images

Only URLs stored inside PostgreSQL.

---

# Kafka Events Published

```
EXPEDITION_CREATED

EXPEDITION_UPDATED

EXPEDITION_CANCELLED

PARTICIPANT_JOINED

PARTICIPANT_LEFT

JOIN_REQUEST_CREATED

JOIN_REQUEST_APPROVED

JOIN_REQUEST_REJECTED

REVIEW_SUBMITTED

PHOTO_UPLOADED
```

---

# Kafka Events Consumed

```
COMMUNITY_DELETED

USER_DELETED

GUIDE_VERIFIED
```

---

# Dependencies

Depends on

Authentication Service

Community Service

User Service

MinIO

Kafka

Redis

PostgreSQL

Does NOT depend on

Recommendation

Notification

Feed

Moderation

---

# Scaling

Heavy expedition planning

↓

Scale Expedition Service independently.

Large gallery uploads

↓

Future media workers.

---

# Folder Structure

```
expedition-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

storage/

events/

workers/

dependencies/

tests/

alembic/

Dockerfile

requirements.txt

README.md
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

---

# Failure Scenarios

Expedition not found

↓

404

---

Already Participant

↓

409

---

Join Request Pending

↓

409

---

Organizer leaves own expedition

↓

400

---

Gallery Upload Failed

↓

500

---

Review before completion

↓

400

---

# Logging

Log

Expedition Created

Participant Joined

Participant Left

Gallery Uploaded

Gear Updated

Review Submitted

Never log

Private participant information

Sensitive notes

---

# Monitoring

Expose

```
/health

/metrics
```

Metrics

Expedition Creation Rate

Join Requests

Participant Growth

Gallery Upload Count

Gear Planner Usage

Review Submission Rate

API Latency

---

# Docker

Runs independently.

Environment Variables

```
DATABASE_URL

MINIO_ENDPOINT

MINIO_ACCESS_KEY

MINIO_SECRET_KEY

REDIS_URL

KAFKA_URL

JWT_PUBLIC_KEY
```

---

# Future Enhancements

Phase 2

- Route Maps
- GPS Checkpoints
- Offline Packing Lists
- Shared Expense Tracking (Optional)
- Polls

Phase 3

- AI Packing Suggestions
- Weather-aware Packing
- Route Optimization
- Smart Equipment Recommendations
- Emergency Contacts

---

# Ownership Summary

Expedition Service owns

✔ Expedition Lifecycle

✔ Join Requests

✔ Participants

✔ Itinerary

✔ Expedition Gallery

✔ Gear Planner

✔ Packing Checklist

✔ Reviews

✔ Expedition Metadata

Expedition Service never owns

✖ Authentication

✖ Community Lifecycle

✖ Stories

✖ Recommendations

✖ Notifications

✖ Chat Infrastructure

✖ Guide Verification

The Expedition Service is the collaborative planning workspace of OntDekker. Every expedition belongs to a single community and provides members with everything needed to organize, prepare for, participate in, and preserve a shared travel experience. It remains focused on expedition management while delegating authentication, messaging infrastructure, recommendations, and notifications to their respective services.


# Part 6 — Guide Service

Version: 1.0

Status: Final

---

# Overview

The Guide Service manages the complete lifecycle of local guides within OntDekker.

Unlike marketplace platforms, guides are not bookable services.

Instead, guides are trusted members of the OntDekker community who help travelers discover authentic local experiences.

The Guide Service is responsible for:

- Guide Applications
- Guide Verification
- Guide Profiles
- Areas Covered
- Languages
- Availability
- Ratings
- Reviews
- Guide–Traveler Relationships
- Travel Connections

This service is the only owner of guide-related information.

---

# Purpose

Provide a trusted ecosystem where verified local guides can connect with travelers and build long-term travel relationships.

---

# Responsibilities

The Guide Service owns the following business capabilities.

---

## Guide Applications

Any registered user can apply to become a guide.

Application contains

- Biography
- Areas Covered
- Languages
- Experience
- Identity Documents
- Certifications (Optional)

Application States

- Draft
- Submitted
- Under Review
- Approved
- Rejected

---

## Guide Verification

Verification includes

- Identity Verification
- Location Verification
- Manual Admin Review

Only approved guides receive

✔ Verified Guide Badge

---

## Guide Profile

Every approved guide has a public profile.

Contains

- Name
- Profile Photo
- Cover Image
- Biography
- Areas Covered
- Languages
- Expertise
- Years of Experience
- Rating
- Review Count
- Verification Badge

---

## Areas Covered

A guide may cover multiple areas.

Example

Japan

- Kyoto
- Osaka
- Nara

India

- Himachal
- Goa
- Ladakh

---

## Languages

Supports multiple languages.

Example

English

Japanese

Hindi

French

Spanish

---

## Availability

Stores

Available

Unavailable

Vacation

Busy

Future

Calendar availability.

---

## Guide Ratings

Average Rating

Review Count

Total Expeditions

Repeat Travelers

---

## Reviews

Travelers can review guides after completing expeditions.

Categories

Knowledge

Friendliness

Communication

Safety

Professionalism

Overall Experience

Would Recommend

---

## Travel Connections

One of OntDekker's unique features.

Stores long-term relationships between guides and travelers.

Tracks

- First Met
- Last Interaction
- Expeditions Together
- Conversation Count
- Photos Shared
- Bookmarked

Users can reconnect with guides they previously traveled with.

---

# Responsibilities NOT Owned

Guide Service never manages

Authentication

Communities

Stories

Expeditions

Chat Messages

Notifications

Recommendations

Payments

Bookings

---

# Database Ownership

Database

```
guide_db
```

Only Guide Service accesses this database.

---

# Database Tables

## guide_profiles

Stores

```
id

user_id

bio

profile_image_url

cover_image_url

years_experience

verification_status

rating

review_count

created_at
```

---

## guide_applications

Stores

```
id

user_id

status

submitted_at

reviewed_at

review_notes
```

---

## guide_locations

Stores

Cities

Regions

Countries

Covered by guide.

---

## guide_languages

Stores

Supported languages.

---

## guide_availability

Stores

Availability status.

---

## guide_reviews

Stores

Traveler reviews.

---

## travel_connections

Stores

Guide–Traveler relationship.

```
guide_id

traveler_id

first_met

last_interaction

expeditions_together

conversation_count

photos_shared

bookmarked
```

---

# Public APIs

## POST

/guides/apply

Submit Guide Application

---

## GET

/guides

Browse Guides

---

## GET

/guides/{id}

Guide Profile

---

## PUT

/guides/{id}

Update Guide Profile

---

## GET

/guides/{id}/reviews

Guide Reviews

---

## POST

/guides/{id}/bookmark

Bookmark Guide

---

## DELETE

/guides/{id}/bookmark

Remove Bookmark

---

## GET

/guides/my-connections

Previously Connected Guides

---

## GET

/guides/{id}/availability

Guide Availability

---

## PUT

/guides/{id}/availability

Update Availability

---

# Internal APIs

Provides

```
Validate Guide

Get Guide Rating

Get Guide Languages

Get Guide Locations

Check Verification Status

Get Travel Connections
```

---

# Guide Application Flow

```
User

↓

Submit Application

↓

Upload Documents

↓

Store in MinIO

↓

Admin Review

↓

Approved

↓

Guide Profile Created

↓

Publish GUIDE_APPROVED Event
```

---

# Traveler Connection Flow

```
Traveler Joins Expedition

↓

Guide Participates

↓

Expedition Completed

↓

Create Travel Connection

↓

Conversation Count Starts

↓

Reconnect Available
```

---

# Review Flow

```
Traveler

↓

Rate Guide

↓

Save Review

↓

Update Average Rating

↓

Publish GUIDE_REVIEWED Event
```

---

# Guide Lifecycle

```
User

↓

Guide Applicant

↓

Under Review

↓

Verified Guide

↓

Inactive

↓

Archived
```

---

# MinIO Integration

Stores

- Profile Photos
- Cover Images
- Verification Documents

Only object URLs stored in PostgreSQL.

---

# Kafka Events Published

```
GUIDE_APPLICATION_SUBMITTED

GUIDE_APPROVED

GUIDE_REJECTED

GUIDE_PROFILE_UPDATED

GUIDE_REVIEWED

GUIDE_BOOKMARKED

TRAVEL_CONNECTION_CREATED
```

---

# Kafka Events Consumed

```
USER_REGISTERED

EXPEDITION_COMPLETED

USER_DELETED
```

Used to

- Create travel connections
- Update guide statistics
- Remove orphaned references

---

# Dependencies

Depends on

Authentication Service

User Service

Expedition Service

MinIO

Kafka

Redis

PostgreSQL

Does NOT depend on

Feed

Recommendation

Notification

Chat Infrastructure

---

# Scaling

Guide traffic grows independently.

Scale Guide Service separately when directory usage increases.

---

# Folder Structure

```
guide-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

storage/

events/

workers/

dependencies/

tests/

alembic/

Dockerfile

requirements.txt

README.md
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

---

# Failure Scenarios

Guide not found

↓

404

---

Application already submitted

↓

409

---

Guide not verified

↓

403

---

Review already submitted

↓

409

---

Document upload failed

↓

500

---

# Logging

Log

Guide Application

Guide Approval

Guide Rejection

Guide Review

Availability Update

Travel Connection Created

Never log

Identity documents

Sensitive verification information

---

# Monitoring

Expose

```
/health

/metrics
```

Metrics

Applications Submitted

Approval Rate

Guide Ratings

Reviews

Travel Connections

API Latency

---

# Docker

Runs independently.

Environment Variables

```
DATABASE_URL

MINIO_ENDPOINT

MINIO_ACCESS_KEY

MINIO_SECRET_KEY

REDIS_URL

KAFKA_URL

JWT_PUBLIC_KEY
```

---

# Future Enhancements

Phase 2

- Guide Portfolios
- Certifications
- Featured Guides
- Regional Rankings

Phase 3

- AI Guide Matching
- Smart Availability
- Guide Insights Dashboard
- Expertise Verification
- Guide Reputation Score

---

# Ownership Summary

Guide Service owns

✔ Guide Applications

✔ Verification

✔ Guide Profiles

✔ Languages

✔ Areas Covered

✔ Availability

✔ Ratings

✔ Reviews

✔ Travel Connections

Guide Service never owns

✖ Authentication

✖ Communities

✖ Expeditions

✖ Stories

✖ Recommendations

✖ Notifications

✖ Messaging Infrastructure

✖ Payments

The Guide Service establishes trust between travelers and verified local experts. It manages the complete guide lifecycle—from application and verification to long-term travel relationships—while remaining independent of expedition management, messaging, and recommendation logic.



# Part 7 — Recommendation Service

Version: 1.0

Status: Final

---

# Overview

The Recommendation Service is responsible for all personalization within OntDekker.

Unlike the Feed Service, which only stores travel stories, the Recommendation Service determines **what content each user should see and in what order**.

It acts as the intelligence layer of the platform.

The Recommendation Service does not own any user-generated content.

Instead, it continuously analyzes user interactions and produces personalized recommendations.

---

# Purpose

Provide intelligent recommendations that help users discover:

- Travel Stories
- Communities
- Expeditions
- Guides

based on their interests and platform activity.

The initial implementation is **rule-based**.

The architecture is designed so machine learning models can replace the ranking engine in future phases without affecting the rest of the platform.

---

# Responsibilities

The Recommendation Service owns the following capabilities.

---

## Personalized Feed Ranking

Ranks stories for every user.

The Feed Service returns chronological stories.

Recommendation Service returns:

```
Story IDs

↓

Rank Score

↓

Ordering
```

Feed Service then retrieves those stories.

---

## Community Recommendations

Suggest communities based on

- Interests
- Joined Communities
- Story Engagement
- Preferred Destinations
- Friends' Communities
- Activity History

---

## Expedition Recommendations

Suggest expeditions using

- Communities Joined
- Preferred Travel Style
- Preferred Budget
- Destination History
- Expedition Difficulty
- User Interests

---

## Guide Recommendations

Recommend guides based on

- Location
- Preferred Activities
- Languages
- Previous Guide Interactions
- Travel Connections

---

## User Interest Profile

Every user has an evolving interest profile.

Example

```
Adventure

85

Photography

73

Camping

91

Culture

32

Wildlife

67
```

This profile changes continuously.

---

## Trending Content

Calculate

Trending Stories

Trending Communities

Trending Expeditions

Trending Guides

Used for new users.

---

## Cold Start Recommendations

New users have no history.

Initial recommendations use

- Selected Interests
- Travel Preferences
- Popular Communities
- Trending Stories

---

## Recommendation Cache

Frequently requested recommendations are cached in Redis.

---

# Responsibilities NOT Owned

Recommendation Service never manages

Stories

Communities

Users

Authentication

Chat

Notifications

Guides

Expeditions

Database CRUD

It only produces rankings.

---

# Database Ownership

Database

```
recommendation_db
```

---

# Database Tables

## user_interest_profiles

Stores

```
user_id

interest

score

updated_at
```

---

## recommendation_history

Stores

Previously served recommendations.

```
user_id

entity_type

entity_id

score

served_at
```

---

## trending_scores

Stores

```
entity_type

entity_id

score

updated_at
```

---

## recommendation_metrics

Stores

CTR

Engagement

Acceptance Rate

Recommendation Performance

---

# Public APIs

## GET

/recommendations/feed

Returns ranked story IDs.

---

## GET

/recommendations/communities

Recommended Communities.

---

## GET

/recommendations/expeditions

Recommended Expeditions.

---

## GET

/recommendations/guides

Recommended Guides.

---

## GET

/recommendations/trending

Trending content.

---

# Internal APIs

Provides

```
Update Interest Profile

Recalculate Scores

Invalidate Cache

Generate Recommendations
```

---

# Feed Recommendation Flow

```
User Opens Discover

↓

Frontend

↓

Feed Service

↓

Recommendation Service

↓

Calculate Ranking

↓

Return Story IDs

↓

Feed Service Fetches Stories

↓

Frontend Displays Personalized Feed
```

---

# Interest Update Flow

```
User Likes Story

↓

Feed Service

↓

Kafka

↓

Recommendation Service

↓

Increase Interest Score

↓

Store Updated Profile

↓

Invalidate Redis Cache
```

---

# Community Recommendation Flow

```
User Joins Community

↓

Kafka

↓

Recommendation Service

↓

Update User Interests

↓

Recommend Similar Communities
```

---

# Guide Recommendation Flow

```
Traveler Completes Expedition

↓

Guide Interaction

↓

Kafka

↓

Recommendation Service

↓

Increase Guide Affinity Score

↓

Future Guide Recommendations Updated
```

---

# Ranking Factors

Story Score

Calculated using

- Story Freshness
- Community Affinity
- Similar Interests
- Previous Engagement
- Story Popularity
- Story Quality Score

---

Community Score

Based on

- Interests
- Joined Communities
- Member Activity
- Community Growth

---

Expedition Score

Based on

- Travel Preferences
- Destination Match
- Budget Match
- Community Match
- Difficulty Match

---

Guide Score

Based on

- Preferred Region
- Languages
- Previous Connections
- Ratings
- Shared Interests

---

# Initial Recommendation Strategy

Phase 1

Pure Rule-Based.

Example

```
IF

Interest = Hiking

AND

Community = Mountain Lovers

THEN

Increase Mountain Stories
```

No AI required.

---

# Future Recommendation Strategy

Phase 3

Possible Machine Learning Pipeline

```
Kafka Events

↓

Feature Engineering

↓

Recommendation Model

↓

Prediction API

↓

Recommendation Service

↓

Feed Ranking
```

No architectural changes required.

---

# Redis Usage

Stores

```
Feed Recommendations

Community Recommendations

Expedition Recommendations

Guide Recommendations

Trending Rankings
```

Cache TTL configurable.

---

# Kafka Events Consumed

```
STORY_CREATED

STORY_LIKED

STORY_SHARED

COMMENT_CREATED

COMMUNITY_JOINED

COMMUNITY_LEFT

EXPEDITION_JOINED

EXPEDITION_COMPLETED

GUIDE_REVIEWED

PROFILE_UPDATED

BADGE_EARNED
```

---

# Kafka Events Published

```
RECOMMENDATION_GENERATED

INTEREST_PROFILE_UPDATED

TRENDING_UPDATED
```

---

# Dependencies

Depends on

Redis

Kafka

PostgreSQL

Feed Service

User Service

Community Service

Guide Service

Expedition Service

Does NOT depend on

Authentication

Notification

Chat

Moderation

---

# Folder Structure

```
recommendation-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

ranking/

feature_engineering/

cache/

events/

workers/

dependencies/

tests/

alembic/

Dockerfile

requirements.txt

README.md
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

Ranking algorithms remain inside the Domain layer.

---

# Failure Scenarios

Recommendation unavailable

↓

Return Trending Content

---

Redis unavailable

↓

Generate recommendations directly

---

Kafka unavailable

↓

Continue using previous interest profile

---

No recommendation history

↓

Use Cold Start Strategy

---

# Logging

Log

Recommendation Generated

Cache Hit

Cache Miss

Interest Updated

Trending Updated

Never log

Personal recommendation reasoning

Private user data

---

# Monitoring

Expose

```
/health

/metrics
```

Metrics

Recommendation Latency

Cache Hit Ratio

CTR

Recommendation Requests

Ranking Time

Kafka Consumer Lag

---

# Docker

Runs independently.

Environment Variables

```
DATABASE_URL

REDIS_URL

KAFKA_URL

JWT_PUBLIC_KEY

CACHE_TTL

TRENDING_REFRESH_INTERVAL
```

---

# Scalability

This service is compute-intensive.

Scale independently.

Separate workers can later be introduced for

- Ranking
- Feature Engineering
- Trending Calculation

---

# Future Enhancements

Phase 2

- Better Rule Engine
- Interest Decay
- Trending Windows
- Similar User Recommendations

Phase 3

- Machine Learning Models
- Embedding-Based Recommendations
- Graph-Based Recommendations
- Reinforcement Learning
- Explainable Recommendations

---

# Ownership Summary

Recommendation Service owns

✔ User Interest Profiles

✔ Feed Ranking

✔ Community Recommendations

✔ Expedition Recommendations

✔ Guide Recommendations

✔ Trending Scores

✔ Recommendation Cache

Recommendation Service never owns

✖ Stories

✖ Communities

✖ Expeditions

✖ Guides

✖ User Profiles

✖ Authentication

✖ Notifications

✖ Chat

The Recommendation Service is the intelligence engine of OntDekker. It continuously learns from user activity through Kafka events, builds evolving interest profiles, and generates personalized recommendations while remaining independent of content ownership. This separation allows the recommendation engine to evolve from a simple rule-based system to advanced machine learning models without requiring changes to other microservices.



# Part 8 — Chat Service

Version: 1.0

Status: Final

---

# Overview

The Chat Service is responsible for all real-time communication across the OntDekker platform.

Unlike the Notification Service, which delivers asynchronous updates, the Chat Service provides instant, bidirectional communication between users.

The Chat Service supports three distinct communication channels:

- Private Chats
- Community Chats
- Expedition Chats

The service is optimized for low latency, high availability, and scalability.

---

# Purpose

Provide secure and reliable real-time communication that enables travelers to collaborate before, during, and after expeditions.

---

# Responsibilities

The Chat Service owns the following capabilities.

---

## Private Messaging

Supports

- One-to-one conversations
- Text messages
- Image sharing
- Message reactions (Future)
- Read receipts
- Typing indicators
- Online status

---

## Community Chat

Every community has a dedicated group chat.

Supports

- Group messaging
- Community announcements
- Images
- File sharing (Future)
- Pinned messages (Future)

Only community members can participate.

---

## Expedition Chat

Every expedition has its own chat.

Supports

- Planning discussions
- Logistics
- Packing discussions
- Photo sharing
- Live coordination

Only expedition participants can access.

---

## Conversation Management

Supports

- Create Conversation
- Archive Conversation
- Delete Conversation (Soft Delete)
- Mute Conversation
- Pin Conversation

---

## Message Management

Supports

- Send Message
- Edit Message
- Delete Message
- Reply to Message
- Forward Message (Future)

---

## Read Receipts

Stores

- Delivered
- Read
- Read Timestamp

---

## Typing Indicators

Real-time event.

No database persistence.

---

## Online Presence

Tracks

- Online
- Offline
- Last Seen

---

## Attachments

Supports

- Images

Future

- Documents
- Voice Notes
- Videos

Media stored in MinIO.

---

# Responsibilities NOT Owned

Chat Service never manages

Authentication

Communities

Stories

Expeditions

Recommendations

Notifications

Guide Profiles

User Profiles

---

# Database Ownership

Database

```
chat_db
```

Only Chat Service accesses this database.

---

# Database Tables

## conversations

Stores

```
id

conversation_type

created_at

updated_at
```

Conversation Types

- PRIVATE
- COMMUNITY
- EXPEDITION

---

## conversation_members

Stores

```
conversation_id

user_id

joined_at
```

---

## messages

Stores

```
id

conversation_id

sender_id

content

message_type

edited

created_at

updated_at
```

---

## attachments

Stores

```
message_id

file_url

file_type
```

---

## read_receipts

Stores

```
message_id

user_id

read_at
```

---

## pinned_messages

Stores

Pinned messages for group chats.

---

# Public APIs

## GET

/chat/conversations

User conversations

---

## GET

/chat/conversations/{id}

Conversation details

---

## GET

/chat/conversations/{id}/messages

Conversation history

---

## POST

/chat/conversations/{id}/messages

Send message

---

## PUT

/chat/messages/{id}

Edit message

---

## DELETE

/chat/messages/{id}

Delete message

---

## POST

/chat/messages/{id}/read

Mark message as read

---

## POST

/chat/conversations/{id}/mute

Mute conversation

---

# WebSocket Endpoints

```
/ws/chat
```

Events

```
CONNECT

DISCONNECT

SEND_MESSAGE

EDIT_MESSAGE

DELETE_MESSAGE

TYPING

STOP_TYPING

READ_MESSAGE

ONLINE

OFFLINE
```

---

# Internal APIs

Provides

```
Validate Conversation

Get Conversation Members

Get Last Message

Get Unread Count

Check Membership
```

---

# Private Chat Flow

```
User Opens Chat

↓

Conversation Exists?

↓

Yes

↓

Load Messages

↓

Open WebSocket

↓

Real-Time Messaging
```

---

# Community Chat Flow

```
Join Community

↓

Automatically Join Community Chat

↓

Receive Messages

↓

Participate
```

---

# Expedition Chat Flow

```
Join Expedition

↓

Automatically Added

↓

Expedition Planning

↓

Real-Time Communication
```

---

# Message Sending Flow

```
Send Message

↓

Validate Membership

↓

Persist Message

↓

Publish MESSAGE_SENT

↓

Broadcast via WebSocket

↓

Store Delivery Status
```

---

# Read Receipt Flow

```
Message Opened

↓

READ Event

↓

Store Timestamp

↓

Notify Sender
```

---

# Typing Indicator Flow

```
User Starts Typing

↓

WebSocket Event

↓

Broadcast

↓

Typing...

↓

Stop Typing

↓

Remove Indicator
```

---

# MinIO Integration

Stores

- Images
- Attachments

Database stores only object URLs.

---

# Kafka Events Published

```
MESSAGE_SENT

MESSAGE_EDITED

MESSAGE_DELETED

CONVERSATION_CREATED
```

---

# Kafka Events Consumed

```
COMMUNITY_CREATED

COMMUNITY_JOINED

COMMUNITY_LEFT

EXPEDITION_CREATED

EXPEDITION_JOINED

EXPEDITION_LEFT

USER_DELETED
```

Used to

- Create chats
- Update memberships
- Remove participants

---

# Dependencies

Depends on

Authentication Service

Community Service

Expedition Service

User Service

Kafka

Redis

MinIO

PostgreSQL

Does NOT depend on

Feed

Recommendation

Guide

Notification

---

# Redis Usage

Stores

- Online Users
- Active Connections
- WebSocket Sessions
- Typing Status

Ephemeral data only.

---

# Folder Structure

```
chat-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

websocket/

storage/

events/

workers/

dependencies/

tests/

alembic/

Dockerfile

requirements.txt

README.md
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

Real-time communication logic remains inside the Domain layer.

---

# Failure Scenarios

Conversation not found

↓

404

---

User not member

↓

403

---

WebSocket disconnected

↓

Reconnect

---

Attachment upload failed

↓

500

---

Redis unavailable

↓

Continue without presence information

---

# Logging

Log

Conversation Created

Message Sent

Message Edited

Message Deleted

Connection Opened

Connection Closed

Never log

Private message content

Sensitive attachments

---

# Monitoring

Expose

```
/health

/metrics
```

Metrics

Active Connections

Messages Per Second

Average Latency

Reconnect Rate

Unread Messages

Attachment Upload Rate

---

# Docker

Runs independently.

Environment Variables

```
DATABASE_URL

REDIS_URL

KAFKA_URL

MINIO_ENDPOINT

MINIO_ACCESS_KEY

MINIO_SECRET_KEY

JWT_PUBLIC_KEY
```

---

# Scalability

Chat traffic can become extremely high.

Scale independently.

Future improvements

- Dedicated WebSocket gateway
- Horizontal socket scaling
- Redis Pub/Sub
- Sticky sessions
- Separate attachment workers

---

# Future Enhancements

Phase 2

- Message Search
- Emoji Reactions
- File Sharing
- Voice Messages

Phase 3

- Video Calling
- Screen Sharing
- AI Message Translation
- AI Conversation Summary
- Offline Sync

---

# Ownership Summary

Chat Service owns

✔ Private Chats

✔ Community Chats

✔ Expedition Chats

✔ Conversations

✔ Messages

✔ Read Receipts

✔ Typing Indicators

✔ Online Presence

✔ Attachments

Chat Service never owns

✖ Authentication

✖ Stories

✖ Communities

✖ Expeditions

✖ Recommendations

✖ Notifications

✖ Guide Profiles

The Chat Service provides OntDekker's real-time communication infrastructure. It enables seamless collaboration between travelers, communities, and expedition participants while remaining independent of content management, notifications, and recommendation logic.


# Part 9 — Notification Service

Version: 1.0

Status: Final

---

# Overview

The Notification Service is responsible for delivering timely, relevant, and non-intrusive notifications across the OntDekker platform.

Unlike the Chat Service, which handles real-time conversations, the Notification Service delivers asynchronous events that inform users about activities related to their account, communities, expeditions, guides, and social interactions.

This service follows an event-driven architecture and primarily consumes Kafka events generated by other services.

---

# Purpose

Provide a centralized notification platform that keeps users informed about important activities while allowing personalized notification preferences.

---

# Responsibilities

The Notification Service owns the following capabilities.

---

## In-App Notifications

Supports notifications for

- Story Likes
- Story Comments
- Story Shares
- Community Invitations
- Community Join Requests
- Community Announcements
- Expedition Invitations
- Expedition Join Request Updates
- Expedition Reminders
- Guide Application Updates
- Guide Approval
- Badge Earned
- New Followers
- Mentions (Future)

---

## Notification Preferences

Every user can configure

- Enable / Disable Notifications
- Community Notifications
- Expedition Notifications
- Social Notifications
- Guide Notifications
- Marketing Notifications (Future)

---

## Notification Status

Supports

Unread

Read

Archived

Deleted

---

## Notification Grouping

Groups similar notifications.

Example

Instead of

```
Rahul liked your story

Sneha liked your story

John liked your story
```

Show

```
3 people liked your story.
```

---

## Notification Center

Displays

Today

Yesterday

Earlier

Supports

Infinite scrolling

Filtering

Search (Future)

---

## Delivery Channels

Current

✔ In-App Notifications

Future

- Push Notifications
- Email Notifications
- SMS Notifications

---

# Responsibilities NOT Owned

Notification Service never manages

Authentication

Stories

Communities

Expeditions

Messages

Recommendations

Guides

Business Logic

It only delivers notifications.

---

# Database Ownership

Database

```
notification_db
```

Only Notification Service accesses this database.

---

# Database Tables

## notifications

Stores

```
id

recipient_id

actor_id

notification_type

title

message

entity_type

entity_id

status

created_at
```

---

## notification_preferences

Stores

```
user_id

community_notifications

expedition_notifications

story_notifications

guide_notifications

system_notifications
```

---

## notification_groups

Stores grouped notification metadata.

---

# Public APIs

## GET

/notifications

User notifications

---

## GET

/notifications/unread

Unread notifications

---

## PUT

/notifications/{id}/read

Mark as read

---

## PUT

/notifications/read-all

Mark all as read

---

## DELETE

/notifications/{id}

Delete notification

---

## GET

/notifications/preferences

Notification settings

---

## PUT

/notifications/preferences

Update settings

---

# Internal APIs

Provides

```
Create Notification

Group Notifications

Check User Preferences

Deliver Notification
```

---

# Notification Creation Flow

Example

```
User Likes Story

↓

Feed Service

↓

Kafka

↓

Notification Service

↓

Check Preferences

↓

Generate Notification

↓

Save

↓

Deliver In-App Notification
```

---

# Community Join Flow

```
User Requests Join

↓

Community Service

↓

Kafka

↓

Notification Service

↓

Notify Community Owner
```

---

# Expedition Reminder Flow

```
Expedition Starts Tomorrow

↓

Scheduled Worker

↓

Generate Reminder

↓

Notify Participants
```

---

# Badge Flow

```
Badge Earned

↓

User Service

↓

Kafka

↓

Notification Service

↓

Congratulations Notification
```

---

# Notification Lifecycle

```
Generated

↓

Delivered

↓

Read

↓

Archived

↓

Deleted
```

---

# Kafka Events Consumed

```
STORY_LIKED

COMMENT_CREATED

USER_FOLLOWED

COMMUNITY_CREATED

COMMUNITY_JOINED

JOIN_REQUEST_CREATED

JOIN_REQUEST_APPROVED

EXPEDITION_CREATED

EXPEDITION_JOINED

EXPEDITION_COMPLETED

GUIDE_APPROVED

GUIDE_REVIEWED

BADGE_EARNED

MESSAGE_SENT
```

---

# Kafka Events Published

Normally none.

Future

```
NOTIFICATION_DELIVERED

NOTIFICATION_FAILED
```

---

# Dependencies

Depends on

Kafka

Redis

PostgreSQL

User Service

Does NOT depend on

Feed

Community

Recommendation

Chat

Guide

---

# Redis Usage

Stores

Unread notification counts

Temporary grouped notifications

Frequently accessed notification summaries

---

# Folder Structure

```
notification-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

events/

workers/

scheduler/

dependencies/

tests/

alembic/

Dockerfile

requirements.txt

README.md
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

---

# Failure Scenarios

Recipient deleted

↓

Discard notification

---

Kafka unavailable

↓

Retry consumer

---

Database unavailable

↓

Retry

↓

Dead Letter Queue (Future)

---

Invalid notification type

↓

Log

↓

Discard

---

# Logging

Log

Notification Generated

Notification Delivered

Notification Read

Notification Deleted

Preference Updated

Never log

Sensitive notification content

---

# Monitoring

Expose

```
/health

/metrics
```

Metrics

Notifications Generated

Unread Count

Read Rate

Delivery Time

Kafka Consumer Lag

Error Rate

---

# Docker

Runs independently.

Environment Variables

```
DATABASE_URL

REDIS_URL

KAFKA_URL

JWT_PUBLIC_KEY
```

---

# Scalability

Scale independently.

Future

Dedicated notification workers

Push delivery workers

Email workers

Retry queues

---

# Future Enhancements

Phase 2

Push Notifications

Email Notifications

Notification Templates

Notification Scheduling

---

Phase 3

Smart Notification Prioritization

AI Digest

Notification Personalization

Cross-device Synchronization

---

# Ownership Summary

Notification Service owns

✔ Notification Generation

✔ Notification Storage

✔ Notification Preferences

✔ Notification Grouping

✔ Read / Unread State

✔ Notification Delivery

Notification Service never owns

✖ Stories

✖ Communities

✖ Expeditions

✖ Messages

✖ Recommendations

✖ Business Logic

The Notification Service acts as OntDekker's asynchronous communication hub. It consumes events from Kafka, respects user preferences, generates meaningful notifications, and delivers them efficiently without affecting the responsiveness of the originating services.



# Part 10 — Moderation Service

Version: 1.0

Status: Final

---

# Overview

The Moderation Service is responsible for maintaining a safe, trustworthy, and respectful environment across the OntDekker platform.

Unlike automated moderation systems that immediately punish users based on reports, OntDekker follows a **human-in-the-loop moderation model**.

Reports are reviewed manually by moderators before any action is taken.

The Moderation Service is responsible for:

- User Reports
- Story Reports
- Community Reports
- Expedition Reports
- Guide Reports
- Chat Reports
- Moderator Actions
- Warnings
- Temporary Suspensions
- Permanent Bans
- Audit Logs
- Moderation History

This service owns all moderation-related workflows.

---

# Purpose

Provide a centralized moderation platform that ensures trust, safety, transparency, and accountability throughout OntDekker.

---

# Responsibilities

The Moderation Service owns the following capabilities.

---

## Reporting System

Users can report

- Users
- Stories
- Communities
- Expeditions
- Guides
- Messages
- Discussions

Each report contains

- Reason
- Description
- Evidence (Optional)
- Timestamp
- Reporter

---

## Report Categories

Supported categories

- Spam
- Harassment
- Fake Identity
- Hate Speech
- Dangerous Content
- Inappropriate Content
- Misinformation
- Scam
- Copyright
- Other

---

## Moderator Dashboard

Moderators can

- View Reports
- Filter Reports
- Assign Reports
- Review Evidence
- Contact Reporter (Future)
- Resolve Reports

---

## Moderator Actions

Possible actions

Ignore Report

Warning

Content Removal

Temporary Suspension

Permanent Ban

---

## Warning System

Supports

- First Warning
- Second Warning
- Final Warning

Warnings remain part of moderation history.

---

## Suspension

Supports

Temporary suspensions.

Example

- 1 Day
- 3 Days
- 7 Days
- 30 Days

---

## Permanent Ban

Disables account.

Authentication Service consumes BAN_USER event.

---

## Audit Logs

Every moderator action is logged.

Stores

- Moderator
- Action
- Target
- Timestamp
- Reason

Audit logs are immutable.

---

## Appeal System (Future)

Users may appeal

Warnings

Suspensions

Bans

---

# Responsibilities NOT Owned

Moderation Service never manages

Authentication

Stories

Communities

Expeditions

Recommendations

Notifications

Messaging

Guide Verification

---

# Database Ownership

Database

```
moderation_db
```

Only Moderation Service accesses this database.

---

# Database Tables

## reports

Stores

```
id

reporter_id

entity_type

entity_id

reason

description

status

created_at
```

---

## moderation_actions

Stores

```
id

report_id

moderator_id

action

reason

created_at
```

---

## warnings

Stores

```
user_id

warning_level

reason

created_at
```

---

## suspensions

Stores

```
user_id

start_time

end_time

reason
```

---

## audit_logs

Stores

All moderator activity.

---

## appeals

Future implementation.

---

# Public APIs

## POST

/reports

Create Report

---

## GET

/reports/my

My Reports

---

## GET

/reports/{id}

Report Details

---

# Moderator APIs

## GET

/moderation/reports

All Reports

---

## PUT

/moderation/reports/{id}

Assign Report

---

## POST

/moderation/actions

Take Action

---

## POST

/moderation/warning

Issue Warning

---

## POST

/moderation/suspend

Suspend User

---

## POST

/moderation/ban

Permanently Ban User

---

## GET

/moderation/audit

Audit Logs

---

# Internal APIs

Provides

```
Check User Status

Get Moderation History

Validate Moderator

Record Audit Log
```

---

# Report Flow

```
User

↓

Create Report

↓

Validate

↓

Save Report

↓

Publish REPORT_CREATED

↓

Moderator Queue
```

---

# Review Flow

```
Moderator

↓

Open Report

↓

Review Evidence

↓

Choose Action

↓

Record Audit Log

↓

Publish MODERATION_ACTION
```

---

# Suspension Flow

```
Moderator

↓

Suspend User

↓

Save Suspension

↓

Publish USER_SUSPENDED

↓

Authentication Service blocks login
```

---

# Ban Flow

```
Moderator

↓

Permanent Ban

↓

Publish USER_BANNED

↓

Authentication Service disables account
```

---

# Report Lifecycle

```
Submitted

↓

Under Review

↓

Resolved

↓

Archived
```

---

# Kafka Events Published

```
REPORT_CREATED

WARNING_ISSUED

USER_SUSPENDED

USER_BANNED

CONTENT_REMOVED

REPORT_RESOLVED
```

---

# Kafka Events Consumed

```
USER_REGISTERED

STORY_CREATED

COMMUNITY_CREATED

EXPEDITION_CREATED

GUIDE_APPROVED
```

Used for maintaining references and moderation history.

---

# Dependencies

Depends on

Authentication Service

Kafka

Redis

PostgreSQL

Does NOT depend on

Feed

Community

Recommendation

Chat

Guide

---

# Redis Usage

Stores

Temporary moderation queues

Frequently accessed moderator dashboards

Cached report statistics

---

# Folder Structure

```
moderation-service/

app/

api/

core/

config/

database/

models/

repositories/

schemas/

services/

events/

workers/

dependencies/

tests/

alembic/

Dockerfile

requirements.txt

README.md
```

---

# Clean Architecture

```
Presentation

↓

Application

↓

Domain

↓

Infrastructure
```

Moderation policies remain inside the Domain layer.

---

# Failure Scenarios

Report not found

↓

404

---

Unauthorized moderator

↓

403

---

Duplicate report

↓

409

---

Invalid action

↓

400

---

Database unavailable

↓

503

---

# Logging

Log

Report Created

Report Assigned

Warning Issued

Suspension

Ban

Moderator Login

Audit Entry

Never log

Private evidence

Personally identifiable documents

Moderator secrets

---

# Monitoring

Expose

```
/health

/metrics
```

Metrics

Reports Submitted

Reports Resolved

Average Resolution Time

Warnings Issued

Suspensions

Ban Count

Moderator Activity

---

# Docker

Runs independently.

Environment Variables

```
DATABASE_URL

REDIS_URL

KAFKA_URL

JWT_PUBLIC_KEY
```

---

# Scalability

Moderation workload grows independently.

Future improvements

- Dedicated moderation workers
- AI-assisted report prioritization
- Automatic spam detection
- Distributed moderation queues

---

# Future Enhancements

Phase 2

- Appeal System
- Content Flagging
- Moderator Assignment Rules
- Report Templates

Phase 3

- AI-assisted Moderation
- Toxicity Detection
- Spam Detection
- Fraud Detection
- Community Health Score
- Moderator Analytics Dashboard

---

# Ownership Summary

Moderation Service owns

✔ Reports

✔ Report Lifecycle

✔ Moderator Actions

✔ Warnings

✔ Suspensions

✔ Permanent Bans

✔ Audit Logs

✔ Moderation History

Moderation Service never owns

✖ Authentication

✖ Stories

✖ Communities

✖ Expeditions

✖ Recommendations

✖ Notifications

✖ Chat

✖ Guide Verification

The Moderation Service is OntDekker's trust and safety backbone. It ensures that reports are reviewed fairly, actions are transparent and auditable, and platform integrity is maintained through human-driven moderation rather than automatic punitive actions. By publishing moderation events instead of directly modifying other services, it preserves loose coupling while enabling the Authentication Service and other services to react appropriately.