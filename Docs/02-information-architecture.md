# OntDekker — Complete UX & Information Architecture Blueprint

> **Version:** 1.0  
> **Document Type:** UX Architecture & Navigation Blueprint  
> **Purpose:** Define the complete information architecture, navigation hierarchy, user journeys, interaction patterns, and application state management for OntDekker.

---

# Table of Contents

1. Overview
2. Application Architecture
3. Navigation Hierarchy
4. Information Architecture
5. Route Structure
6. Screen Inventory
7. Overlay System
8. User Journeys
9. Interaction & State Matrix
10. Global UX Principles

---

# 1. Overview

This document represents the complete high-fidelity reverse-engineered Navigation and Information Architecture for **OntDekker**, a premium slow-travel platform.

Rather than treating every feature as an independent page, OntDekker is designed as a **Single Page Application (SPA)** where every workspace exists inside one persistent application shell.

The objective is to:

- Preserve navigation context
- Reduce unnecessary page reloads
- Maintain user immersion
- Encourage uninterrupted exploration
- Minimize cognitive load

---

# 2. Application Architecture

```
Landing
      │
      ▼
┌─────────────────────────────┐
│ Main Application Container  │
└─────────────────────────────┘
      │
      ├──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼
Top Navbar      Sidebar        Global Search
```

---

## Main Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│                       Top Navigation                         │
├───────────────┬───────────────────────────────┬──────────────┤
│               │                               │              │
│               │                               │              │
│   Sidebar     │        Active Workspace       │ Right Panel* │
│               │                               │              │
│               │                               │              │
└───────────────┴───────────────────────────────┴──────────────┘
```

> *Optional contextual drawer depending on the current workspace.*

---

# 3. Navigation Hierarchy

## Top Navigation

Responsible for global application controls.

```
Top Navigation
│
├── Notifications
├── Messages
├── Search
├── Profile
└── User Menu
```

---

## Sidebar Navigation

Primary application navigation.

```
Sidebar
│
├── Discover
├── Communities
├── My Trips
├── Guides
├── Profile
└── Settings
```

---

## Global Search

Global search provides categorized results.

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

# 4. Information Architecture

```
Application
│
├── Discover
│
├── Communities
│
├── My Trips
│
├── Guides
│
├── Messages
│
├── Profile
│
└── Settings
```

---

## Discover

```
Discover
│
├── Feed
├── Story Modal
├── Recommendations
└── Planning Widget
```

---

## Communities

```
Communities
│
├── Community Feed
├── Expeditions
├── Members
└── About
```

---

## My Trips

```
My Trips
│
├── Active Trips
├── Upcoming Trips
└── Expedition Workspace
        │
        ├── Overview
        ├── Discussion
        ├── Packing
        ├── Gallery
        └── Members
```

---

## Guides

```
Guides
│
├── Discover Guides
├── My Guides
└── Guide Portfolio
        │
        ├── Reviews
        ├── Certifications
        ├── Journey Timeline
        └── Invite to Expedition
```

---

## Messages

```
Messages
│
├── Private Chats
├── Community Chats
└── Expedition Chats
```

---

## Profile

```
Profile
│
├── Journal
├── Saved Stories
├── Saved Guides
└── Settings
```

---

# 5. Route Structure

```
/
│
├── /discover
│     ├── /story/:id
│     └── /planning-workspace/:id
│
├── /communities
│     └── /community/:id
│            ├── Feed
│            ├── Expeditions
│            ├── Members
│            └── About
│
├── /my-trips
│     └── /expedition/:id
│            ├── Overview
│            ├── Discussion
│            ├── Packing
│            ├── Gallery
│            └── Members
│
├── /guides
│     ├── Discover
│     ├── My Guides
│     └── Guide Profile
│
├── /profile
│
└── /messages
      ├── Private
      ├── Community
      └── Expedition
```

---

# 6. Screen Inventory

---

## Discover

### Purpose

Social discovery feed.

### Entry

- Application launch
- Sidebar

### Exit

- Story
- Messages
- Expedition
- Communities

---

## Communities

### Purpose

Community exploration.

### Entry

Sidebar.

### Exit

- Community
- Search
- Sidebar

---

## Community Details

### Purpose

Community workspace.

### Tabs

- Feed
- Expeditions
- Members
- About

---

## Expedition Workspace

### Purpose

Trip planning.

### Tabs

- Overview
- Discussion
- Packing
- Gallery
- Members

---

## Guides

### Purpose

Guide discovery.

### Sections

- Discover
- My Guides
- Guide Portfolio

---

## Messages

### Purpose

Unified communication center.

### Channels

- Private
- Community
- Expedition

---

# 7. Overlay System

OntDekker uses contextual overlays instead of navigating users away from their workflow.

---

## Floating Create Menu

Trigger

Floating Action Button.

```
Create
│
├── Story
├── Community
└── Expedition
```

---

## Story Modal

Trigger

Click Story Card.

Contains

- Gallery
- Comments
- Bookmark
- Community
- Author

---

## Guide Invitation Modal

Trigger

Invite to Expedition.

Flow

```
Guide
      │
      ▼
Select Expedition
      │
      ▼
Confirmation
```

If no expedition exists:

```
No Trips
      │
      ▼
Create Expedition Prompt
```

---

## Notifications Drawer

Trigger

Bell icon.

Organization

```
Notifications
│
├── Today
├── Yesterday
└── Earlier
```

---

# 8. User Journeys

---

## Journey A — Finding a Guide

```
Discover
      │
      ▼
Guides
      │
      ▼
Search
      │
      ▼
Guide Portfolio
      │
      ▼
Invite
      │
      ▼
Success
```

---

## Journey B — Packing Planner

```
My Trips
      │
      ▼
Expedition
      │
      ▼
Packing
      │
      ▼
Add Item
      │
      ▼
Weight Updated
      │
      ▼
Packing Classification Updated
```

---

## Journey C — Continue Conversation

```
Guides
      │
      ▼
My Guides
      │
      ▼
Reconnect
      │
      ▼
Messages
      │
      ▼
Chat Opens Automatically
```

---

# 9. Interaction & State Matrix

| Module | Active State | Loading | Empty | Error |
|----------|-------------|----------|--------|-------|
| Discover Feed | Interactive stories | Skeleton cards | No stories available | Feed loading failed |
| Search | Categorized results | Search loader | No results | Search unavailable |
| Guides | Verified guide cards | Skeleton profiles | No guides found | Unable to load guides |
| Messages | Live conversations | Loading spinner | Start a conversation | Failed to send message |
| Expedition Workspace | Planning tools | Workspace loading | No packing items | Workspace update failed |

---

# 10. Global UX Principles

## Context Preservation

Users should never lose context while exploring content.

Story details, profiles, and planning tools open using overlays whenever possible.

---

## Lightweight Feedback

Every interaction provides immediate feedback through:

- Toast notifications
- Loading indicators
- Success animations
- Error recovery

---

## Progressive Disclosure

Complex features are divided into tabs rather than separate pages.

Examples include:

- Communities
- Expeditions
- Guides

This minimizes cognitive load.

---

## SPA-First Navigation

All major features exist within a persistent application shell.

Benefits include:

- Faster transitions
- Reduced loading times
- Persistent navigation
- Better state management

---

## Consistent Interaction Patterns

Every major workspace follows the same interaction model:

```
Navigation
        │
        ▼
Workspace
        │
        ▼
Tabs
        │
        ▼
Actions
        │
        ▼
Contextual Overlays
```

This consistency ensures users always understand where they are, what they can do next, and how to return without losing their place.

---

# UX Design Principles

- Utility over entertainment
- Calm interfaces over visual clutter
- Preserve user context
- Prioritize readability
- Progressive disclosure of complexity
- Consistent navigation hierarchy
- Offline-friendly interaction patterns
- Fast, uninterrupted workflows
- Minimal cognitive load
- Purposeful animations only
- Every interaction provides immediate feedback