# OntDekker Component Library & Architectural Blueprint

> **Version:** 1.0  
> **Document Type:** Component Library & Frontend Architecture  
> **Technology Stack:** React 18+, TypeScript, Tailwind CSS, Motion (`motion/react`), Lucide React  
> **Purpose:** Define the reusable UI components, architecture, TypeScript interfaces, interaction patterns, and implementation standards for the OntDekker frontend.

---

# Table of Contents

1. Architecture Principles
2. Component Architecture
3. Base Layout Components
4. Navigation Components
5. Card Components
6. Overlay Components
7. Content Components
8. Header Components
9. Component Development Standards

---

# 1. Architecture Principles

Every reusable component follows four core principles.

---

## State Isolation

Components remain as stateless as possible.

State should be passed through:

- Props
- Callbacks
- Context Providers
- Global Store

---

## Tailwind First

All styling is implemented using Tailwind utility classes.

Avoid CSS modules unless absolutely necessary.

---

## Motion Integration

Animations are powered using:

```tsx
motion/react
```

Animations should remain subtle and functional.

---

## Accessibility First

Every interactive component must support:

- Keyboard navigation
- Focus management
- ARIA labels
- Screen readers
- High contrast

---

# 2. Component Architecture

```
Application
│
├── Layout Components
│
├── Navigation Components
│
├── Cards
│
├── Overlays
│
├── Content Components
│
└── Header Components
```

---

# 3. Base Layout Components

---

# Navbar

## Purpose

Global application header providing:

- Branding
- Navigation
- Notifications
- Profile Access

---

## Props

```typescript
interface NavbarProps {
  currentView: string;
  navigateTo: (view: string, id?: string) => void;
  user: {
    name: string;
    avatar: string;
  };
  unreadNotificationsCount: number;
}
```

---

## Variants

### Default

Desktop floating navigation.

### Compact

Used inside overlays and modals.

---

## States

- Active Navigation
- Notification Badge
- Mobile Collapse

---

## Accessibility

```html
<nav role="navigation">
```

---

# Sidebar

## Purpose

Primary application navigation.

---

## Props

```typescript
interface SidebarProps {
  currentView: string;
  navigateTo: (view: string, id?: string) => void;
  items: NavigationItem[];
}
```

---

## States

Hover

```css
hover:bg-gray-50
```

Active

- Left indicator
- Active background

---

# Button

## Purpose

Reusable action component.

---

## Props

```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "xs" | "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ComponentType<any>;
  iconPosition?: "left" | "right";
}
```

---

## Variants

### Primary

```css
bg-black

text-white

hover:bg-neutral-800
```

---

### Secondary

```css
bg-gray-100

text-gray-900
```

---

### Outline

```css
border

bg-white
```

---

### Ghost

Transparent

---

### Danger

Destructive actions.

---

# Avatar

## Purpose

Display user identity.

---

## Props

```typescript
interface AvatarProps {
  src: string;
  alt: string;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  status?: "online" | "offline" | "none";
}
```

---

## Sizes

| Size | Class |
|------|---------|
| xs | `w-6 h-6` |
| sm | `w-8 h-8` |
| md | `w-12 h-12` |
| lg | `w-16 h-16` |
| xl | `w-32 h-32` |

---

# Badge

## Purpose

Display status and metadata.

---

## Props

```typescript
interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "info" | "error";
  size?: "sm" | "md";
}
```

---

## Variants

Default

Success

Warning

Info

Error

---

# 4. Navigation Components

---

# Search

## Purpose

Global filtering component.

---

## Props

```typescript
interface SearchProps {
  placeholder?: string;
  value: string;
  onChange:(query:string)=>void;
  onClear?:()=>void;
}
```

---

## States

Focused

- Black border
- Shadow increase

Typing

- Clear button appears

---

# Dropdown

## Purpose

Selection menu.

---

## Props

```typescript
interface DropdownProps{
   trigger:React.ReactNode;
   items:DropdownItem[];
   onSelect:(value:string)=>void;
}
```

---

## Motion

```tsx
initial={{
opacity:0,
y:-4,
scale:0.95
}}
```

↓

```tsx
animate={{
opacity:1,
y:0,
scale:1
}}
```

---

# Tabs

## Purpose

Switch between sections inside the same workspace.

---

## Props

```typescript
interface TabsProps{
    tabs:TabItem[];
    activeTabId:string;
    onChange:(id:string)=>void;
}
```

---

# 5. Card Components

---

# Base Card

## Purpose

Reusable card container.

---

## Props

```typescript
interface BaseCardProps{
    children:React.ReactNode;
    onClick?:()=>void;
    className?:string;
    interactive?:boolean;
}
```

---

# Community Card

## Purpose

Community preview.

---

## Information

- Cover
- Name
- Members
- Description
- Join State

---

## Props

```typescript
interface CommunityCardProps{
    community:Community;
    isJoined:boolean;
    onJoinToggle:(e:React.MouseEvent)=>void;
    onClick:()=>void;
}
```

---

# Guide Card

## Purpose

Guide discovery.

---

## Information

- Avatar
- Rating
- Cities
- Languages
- Bio

---

## Actions

- Bookmark
- Message
- View Profile

---

## Props

```typescript
interface GuideCardProps{
    guide:Guide;
    onBookmarkToggle:(e:React.MouseEvent)=>void;
    onMessage:(e:React.MouseEvent)=>void;
    onClick:()=>void;
}
```

---

# Story Card

## Purpose

Editorial travel journal preview.

---

## Information

- Author
- Cover Image
- Reading Time
- Pace
- Location
- Tags

---

## Actions

- Like
- Save
- Comment
- Open Story

---

## Props

```typescript
interface StoryCardProps{
    post:Post;
    onLikeToggle:()=>void;
    onSaveToggle:()=>void;
    onCommentClick:()=>void;
    onClick:()=>void;
}
```

---

# Trip Card

## Purpose

Represent an expedition.

---

## Information

- Destination
- Dates
- Budget
- Organizer
- Status

---

## Props

```typescript
interface TripCardProps{
    trip:Trip;
    onClick:()=>void;
}
```

---

# 6. Overlay Components

---

# Modal

## Purpose

Reusable overlay container.

---

## Props

```typescript
interface ModalProps{
    isOpen:boolean;
    onClose:()=>void;
    title:string;
    children:React.ReactNode;
}
```

---

# Dialog

## Purpose

Confirmation workflow.

---

## Props

```typescript
interface DialogProps{
    isOpen:boolean;
    title:string;
    message:string;
    confirmLabel?:string;
    cancelLabel?:string;
    onConfirm:()=>void;
}
```

---

# Drawer

## Purpose

Mobile-first bottom sheet.

---

## Props

```typescript
interface DrawerProps{
    isOpen:boolean;
    onClose:()=>void;
    title:string;
    children:React.ReactNode;
}
```

---

# Toast

## Purpose

Temporary notification.

---

## Props

```typescript
interface ToastProps{
    message:string;
    type?:"success"|"info"|"error";
    onDismiss:()=>void;
}
```

---

# 7. Content Components

---

# Chat Bubble

## Purpose

Conversation message.

---

## Props

```typescript
interface ChatBubbleProps{
    message:ChatMessage;
    isCurrentUser:boolean;
}
```

---

## Variants

- Incoming
- Outgoing
- Guide
- System

---

# Timeline

## Purpose

Chronological display.

Used for:

- Itinerary
- Journey Timeline
- Packing Timeline

---

## Props

```typescript
interface TimelineProps{
    items:TimelineItem[];
    interactive?:boolean;
}
```

---

# Image Carousel

## Purpose

Travel gallery.

---

## Props

```typescript
interface ImageCarouselProps{
    images:string[];
    aspectRatio?:
        |"video"
        |"square"
        |"auto";
}
```

---

# Comment

## Purpose

Story discussion.

---

## Props

```typescript
interface CommentProps{
    comment:Comment;
}
```

---

# Notification

## Purpose

Inbox activity item.

---

## Types

- Invite
- Like
- Comment
- System

---

## Props

```typescript
interface NotificationProps{
    notification:Notification;
    onAction?:(id:string)=>void;
}
```

---

# 8. Header Components

---

# Profile Header

## Purpose

Top section of user profiles.

---

## Information

- Cover
- Avatar
- Bio
- Stats
- Edit Profile

---

## Props

```typescript
interface ProfileHeaderProps{
    user:User;
    onEditToggle:()=>void;
}
```

---

# Community Header

## Purpose

Community landing section.

---

## Information

- Banner
- Description
- Members
- Rules
- Join Button

---

## Props

```typescript
interface CommunityHeaderProps{
    community:Community;
    isJoined:boolean;
    onJoinToggle:()=>void;
}
```

---

# Expedition Header

## Purpose

Trip overview section.

---

## Information

- Destination
- Budget
- Dates
- Organizer
- Cover

---

## Props

```typescript
interface ExpeditionHeaderProps{
    trip:Trip;
    onBack:()=>void;
}
```

---

# 9. Component Development Standards

## Naming Convention

```
ComponentName.tsx

ComponentName.types.ts

ComponentName.styles.ts (optional)

index.ts
```

---

## Folder Structure

```
components/

├── layout/
│   ├── Navbar/
│   ├── Sidebar/
│   └── Footer/
│
├── navigation/
│   ├── Tabs/
│   ├── Search/
│   └── Dropdown/
│
├── cards/
│   ├── BaseCard/
│   ├── StoryCard/
│   ├── GuideCard/
│   ├── CommunityCard/
│   └── TripCard/
│
├── overlays/
│   ├── Modal/
│   ├── Dialog/
│   ├── Drawer/
│   └── Toast/
│
├── content/
│   ├── ChatBubble/
│   ├── Timeline/
│   ├── Comment/
│   ├── Notification/
│   └── ImageCarousel/
│
└── headers/
    ├── ProfileHeader/
    ├── CommunityHeader/
    └── ExpeditionHeader/
```

---

## Development Rules

Every component should:

- Be reusable and composable
- Receive data exclusively through props
- Avoid business logic inside UI components
- Support dark/light theme extensions (future-ready)
- Be fully typed with TypeScript interfaces
- Follow OntDekker's Design System tokens
- Support keyboard navigation and accessibility
- Include subtle motion using `motion/react`
- Preserve consistent spacing, typography, and interaction patterns

---

# Component Philosophy

The OntDekker Component Library is built around **modularity, composability, and consistency**. Every component is designed as an isolated building block that integrates seamlessly with the platform's Swiss-editorial design language, ensuring a maintainable, scalable, and accessible frontend architecture while delivering a calm, premium user experience.