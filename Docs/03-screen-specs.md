# OntDekker — Product Design & Screen Architecture Blueprint

> **Version:** 1.0  
> **Document Type:** Product Design & Screen Architecture  
> **Purpose:** Define the complete interaction architecture, screen specifications, data requirements, animations, responsive behavior, accessibility standards, and design constraints for every major screen of the OntDekker platform.

---

# Table of Contents

1. Global Navigation
2. Global Search
3. Discover Module
4. Communities Module
5. Expedition Module
6. Guides Module
7. Messaging Module
8. Global Creation System
9. Screen Transition Matrix
10. Design System Constraints
11. Final Architectural Adjustments

---

# 1. Global Navigation

## Purpose

Provide persistent navigation across the application while maintaining user orientation and application state.

---

## Desktop Layout

```
┌──────────────────────────────────────────────────────┐
│                  Top Navigation                       │
├───────────────┬──────────────────────────────┬────────┤
│               │                              │        │
│   Sidebar     │     Active Workspace         │ Drawer │
│               │                              │        │
└───────────────┴──────────────────────────────┴────────┘
```

---

## Mobile Layout

```
────────────────────────
Current Screen

Floating Create Button

Bottom Navigation
────────────────────────
```

---

## Primary Navigation

- Discover
- Communities
- My Trips
- Guides
- Profile
- Settings

---

## Secondary Navigation

- Global Search
- Notifications
- Messages
- User Profile

---

## Required Data

- User Profile
- Notification Count
- Unread Messages

---

## API Dependencies

```
GET /api/user/profile

GET /api/notifications/unread
```

---

## Animations

### Entry

- Sidebar slides from left
- Fade duration: 0.2s

### Exit

- Quick fade
- Responsive collapse transition

---

## States

### Loading

- Avatar skeleton

### Success

- Active route indicator

### Error

- Text-only fallback

---

## Responsive Rules

Desktop

- Permanent sidebar

Mobile

- Bottom navigation
- Floating Create button

---

## Accessibility

- aria-current
- 44px touch targets
- Keyboard navigation

---

# 2. Global Search

## Purpose

Search every major content type from one location.

---

## Search Categories

```
Search
│
├── Stories
├── Communities
├── Expeditions
├── Guides
└── Users
```

---

## User Actions

- Type
- Select Result
- Keyboard Navigation
- Escape to Close

---

## Required Data

Entire searchable collections

---

## API

```
GET /api/search?q=query
```

---

## Animations

Entry

- Scale Up
- Slide Down

Exit

- Fade Out

---

## States

### Loading

Spinner inside input

### Empty

```
No results found.
```

### Success

Grouped result grid

### Error

Red outline with helper message

---

## Responsive

Desktop

Dropdown

Mobile

Fullscreen overlay

---

## Accessibility

- role="listbox"
- Arrow navigation
- Focus trap

---

# 3. Discover Module

---

# Discover Screen

## Purpose

Primary exploration experience.

---

## User Goals

- Read stories
- Discover expeditions
- Explore communities

---

## Primary CTA

Read Story

---

## Secondary Actions

- Like
- Bookmark
- Comment
- Share

---

## Visible Information

- Greeting Dashboard
- Expedition Status
- Pending Requests
- Messages
- Story Cards
- Images
- Community Tags
- Read Time

---

## Hidden Information

- Full comments
- Long-form story

---

## API

```
GET /api/posts

GET /api/feed/filters
```

---

## Animations

- Card stagger
- Scroll reveal

---

## States

Loading

Skeleton Cards

Empty

```
No stories available.
```

Success

Editorial feed

Error

Retry Banner

---

## Responsive

Desktop

```
Feed
+
Right Sidebar
```

Mobile

Single column

---

# Story Modal

## Purpose

Immersive story reading experience.

---

## Contents

- Story
- Gallery
- Comments
- Community
- Author
- Bookmark

---

## User Actions

- Swipe gallery
- Comment
- Like
- Bookmark

---

## API

```
GET /api/posts/{id}

GET /api/posts/{id}/comments
```

---

## Animations

Backdrop Fade

Card Scale

---

## States

Loading Spinner

Success Editorial Layout

Error

```
Story failed to load.
```

---

## Responsive

Desktop

Centered modal

Mobile

Fullscreen

---

# 4. Communities Module

---

# Community Directory

## Purpose

Community discovery.

---

## User Actions

- Join
- Search
- Filter

---

## Visible Information

- Banner
- Name
- Members
- Category
- Description

---

## API

```
GET /api/communities

POST /api/communities/join
```

---

## States

Loading

Community Skeleton

Empty

```
No communities found.
```

---

# Community Workspace

## Tabs

```
Feed

Expeditions

Members

About
```

---

## Features

- Discussions
- Events
- Member Directory
- Rules

---

## API

```
GET /api/communities/{id}
```

---

## Responsive

Desktop Tabs

↓

Scrollable Mobile Tabs

---

# 5. Expedition Module

---

# My Trips

## Purpose

Manage expeditions.

---

## Visible Information

- Location
- Dates
- Organizer
- Status

---

## API

```
GET /api/trips
```

---

## States

Loading

Trip Cards

Empty

```
No upcoming trips.
```

---

# Expedition Workspace

## Tabs

```
Overview

Discussion

Packing

Gallery

Members
```

---

## Features

### Overview

- Budget
- Maps
- Organizer

---

### Discussion

- Chat
- Logistics

---

### Packing

- Weight Optimizer
- Categories
- Checklists

---

### Gallery

Shared Photos

---

### Members

Roster

---

## APIs

```
GET /api/trips/{id}

GET /api/trips/{id}/gear

GET /api/trips/{id}/messages

GET /api/trips/{id}/photos
```

---

## Responsive

Desktop

```
Workspace

+

Quick Panel
```

Mobile

Single scrolling layout

---

# 6. Guides Module

---

# Guides Directory

## Purpose

Discover verified guides.

---

## Filters

- Country
- Language
- Rating
- Specialty
- Verified Only

---

## Guide Card

- Photo
- Rating
- Specialty
- Bio
- Verification

---

## APIs

```
GET /api/guides

GET /api/guides/search
```

---

## States

Loading

Guide Skeleton

Empty

```
No guides found.
```

---

# Guide Portfolio

## Sections

- Cover
- Certifications
- Reviews
- Expeditions
- Gallery
- Journey Together

---

## Primary Actions

- Invite
- Message

---

## Secondary Actions

- Bookmark
- Connect
- Review

---

## APIs

```
GET /api/guides/{id}

GET /api/guides/{id}/reviews

POST /api/guides/{id}/invite
```

---

## Responsive

Desktop

Two Columns

Mobile

Single Column

---

# 7. Messaging Module

---

# Messenger

## Purpose

Unified communication center.

---

## Conversation Types

```
Private

Guide

Community

Expedition
```

---

## Features

- Text
- Images
- Typing
- Read Status

---

## APIs

```
GET /api/messages

GET /api/messages/{conversationId}
```

---

## Responsive

Desktop

```
Conversation List

+

Chat Window
```

Mobile

Conversation List

↓

Chat Screen

---

## States

Loading

Chat Skeleton

Empty

```
Select a conversation.
```

Success

Realtime Messaging

---

# 8. Global Creation System

---

# Floating Create Button

## Purpose

Universal creation entry point.

---

## Options

```
Create

│

├── Story

├── Community

└── Expedition
```

---

## Animation

Backdrop Blur

↓

Cards Scale Up

---

# Creation Forms

## Story

- Title
- Cover
- Body
- Tags

---

## Community

- Name
- Banner
- Visibility
- Rules

---

## Expedition

- Destination
- Dates
- Budget
- Community

---

## APIs

```
POST /api/posts/create

POST /api/communities/create

POST /api/trips/create
```

---

## Success Flow

```
Submit

↓

Toast

↓

Modal Close

↓

Open New Workspace
```

---

# 9. Screen Transition Matrix

| From | To | Trigger | Animation | State Preservation |
|------|----|----------|------------|--------------------|
| Discover | Story | Read Story | Scale Modal | Feed Position |
| Discover | Messages | Header Chat | Horizontal Slide | Active Conversation |
| Guides | Guide Profile | View Profile | Right Slide | Search Filters |
| Guide Profile | Messages | Message | Slide | Active Guide |
| Any Screen | Create | Create Button | Blur + Scale | Freeze Background |
| Community | Expedition | Expedition Card | Vertical Slide | Community Context |

---

# 10. Design System Constraints

## Layout

- Maximum Width: `max-w-5xl`
- Horizontal Padding: `px-6`
- Vertical Padding: `p-6` to `p-8`

---

## Colors

Background

```
#FCFBF9
```

Typography

```
#111111
```

Accent Colors

- Forest Green
- Warm Amber
- Pastel Blue

---

## Typography

### Headings

Space Grotesk

---

### Body

Inter

---

### Technical Data

JetBrains Mono

---

## Design Rules

- Large whitespace
- Editorial layouts
- No dashboard clutter
- No fake technical indicators
- Human-first visual hierarchy

---

# 11. Final Architectural Adjustments

## Discover

- Removed redundant "Recommended Stories"
- Simplified editorial feed
- Cleaner visual hierarchy

---

## Dynamic Dashboard

Replaced the oversized welcome banner with a compact status row displaying:

- Upcoming Expeditions
- Pending Requests
- Unread Messages
- Community Updates

---

## Guides

Expanded into a dedicated module featuring:

- Advanced filtering
- Portfolio pages
- Journey Together timeline
- Client reviews
- Invitation workflow

---

## Engineering Quality

The architecture follows:

- Component isolation
- Type-safe React patterns
- Optimized state management
- Responsive-first layouts
- Accessible interaction models
- Minimalist premium design language

---

# Design Philosophy

OntDekker is designed around **calm exploration rather than rapid consumption**.

Every screen, interaction, animation, and workflow emphasizes:

- Utility over distraction
- Authentic travel over tourism
- Long-form storytelling over short-form content
- Community collaboration over individual consumption
- Minimal interfaces with generous whitespace
- Smooth, uninterrupted navigation within a persistent application shell