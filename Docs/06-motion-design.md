# OntDekker Motion System & UX Interaction Guidelines

> **Version:** 1.0  
> **Document Type:** Motion Design System & UX Interaction Guidelines  
> **Role:** Senior UX Motion Designer  
> **Purpose:** Define the complete motion language, interaction behaviors, animation tokens, transition patterns, and micro-interactions that create OntDekker's calm, premium slow-travel experience.

---

# Table of Contents

1. Motion Philosophy
2. Motion Tokens
3. Interaction States
4. Page & Layout Transitions
5. Overlay Animations
6. Scroll & Sticky Behavior
7. Micro-Interactions
8. Notification Animations
9. Motion Accessibility Principles

---

# 1. Motion Philosophy

Motion in OntDekker is never decorative.

Every animation exists to:

- Improve orientation
- Reinforce hierarchy
- Communicate system state
- Make interactions feel tangible
- Slow the experience into a calm, intentional rhythm

The overall motion language should resemble the movement of **paper, wood, linen, and clay** rather than fast-moving digital interfaces.

---

# Core Motion Principles

## Spatial Orientation

Animations help users understand:

- Where they came from
- Where they are
- Where they are going

---

## Material Hierarchy

Motion reinforces:

- Elevation
- Layering
- Touch feedback
- Surface depth

---

## Calm Interaction

Every transition should feel:

- Slow
- Smooth
- Predictable
- Intentional

Avoid flashy or exaggerated animations.

---

# 2. Motion Tokens

---

## Duration Tokens

| Token | Duration | Usage |
|--------|----------|----------------------------|
| Instant | 100ms | Hover, icon changes |
| Responsive | 200ms | Buttons, focus states |
| Medium | 300ms | Modals, drawers, cards |
| Intimate | 450ms | Page transitions, immersive views |

---

## Easing Curves

### Standard

```
cubic-bezier(0.4,0,0.2,1)
```

Default interaction easing.

---

### Decelerate

```
cubic-bezier(0,0,0.2,1)
```

Used for elements entering the screen.

---

### Accelerate

```
cubic-bezier(0.4,0,1,1)
```

Used for exits.

---

### Organic Spring

```
cubic-bezier(0.34,1.56,0.64,1)
```

Used for:

- Likes
- Bookmarks
- Success animations

---

# 3. Interaction States

---

# Hover

## Purpose

Communicate interactivity.

---

### Trigger

Mouse enters element.

---

### Duration

```
200ms
```

---

### Animation

```
Scale

1.000

↓

1.015
```

Shadow

```
shadow-xs

↓

shadow-md
```

Background

Increase opacity by approximately 5%.

---

# Click

## Purpose

Simulate physical button press.

---

### Trigger

Mouse Down

Touch Start

---

### Duration

```
100ms
```

---

### Animation

```
Scale

1.000

↓

0.97
```

Shadow compresses.

---

# Focus

## Purpose

Highlight active input.

---

### Trigger

Input focus.

---

### Duration

```
200ms
```

---

### Animation

Border

```
Neutral 900
```

Ring

```
ring-1.5
```

Background

```
Gray

↓

White
```

---

# Loading

## Purpose

Reduce perceived waiting time.

---

### Spinner

Continuous rotation

```
360°
```

---

### Skeleton

Opacity

```
30%

↓

80%

↓

30%
```

Cycle

```
1.5 seconds
```

---

# Success

## Purpose

Reward completed actions.

---

### Trigger

Successful API response.

---

### Duration

```
400ms
```

---

### Animation

```
0.9

↓

1.05

↓

1.0
```

Color

Emerald wash.

---

# Failure

## Purpose

Draw attention to problems.

---

### Duration

```
350ms
```

---

### Animation

```
← → ← →
```

Shake

```
±6px
```

Color

Red border.

---

# 4. Page & Layout Transitions

---

# Page Transition

## Trigger

Navigation.

---

### Duration

```
300ms
```

---

### Animation

```
Opacity

0

↓

100
```

```
Y

12px

↓

0px
```

---

# Card Expansion

## Purpose

Open detail screens.

---

### Duration

```
400ms
```

---

### Animation

Card

```
Thumbnail

↓

Expanded Canvas
```

Children

```
Y:10

↓

Y:0
```

with stagger

```
50ms
```

---

# View Stagger

Lists enter sequentially.

```
Card 1

↓

Card 2

↓

Card 3
```

---

# 5. Overlay Animations

---

# Modal

## Trigger

Create

Edit

Invite

---

### Duration

```
300ms
```

---

### Animation

Backdrop

```
Opacity

0

↓

45%
```

Card

```
Scale

0.95

↓

1.0
```

---

# Drawer

## Mobile

---

### Duration

```
350ms
```

---

### Animation

```
Y

100%

↓

0%
```

Backdrop fades simultaneously.

---

# Dialog

Simple scale

```
0.96

↓

1
```

---

# 6. Scroll & Sticky Behavior

---

# Smooth Scrolling

Every internal anchor uses

```css
scroll-behavior: smooth;
```

---

# Sticky Header

When scrolling

Background

```
Transparent

↓

White 80%
```

Blur

```
backdrop-blur-md
```

Border

```
Bottom Border Appears
```

---

# Parallax Images

Background images move at

```
15%

Scroll Speed
```

Ratio

```
0.15x
```

Used only for:

- Story Covers
- Hero Images
- Destination Photography

---

# 7. Micro-Interactions

---

# Accordion

Chevron

```
0°

↓

180°
```

Duration

```
150ms
```

---

# Comment Expansion

Height

```
0

↓

Auto
```

Comments appear using

```
40ms
```

stagger intervals.

---

# Like Animation

Heart

```
0.8

↓

1.3

↓

1
```

Uses

Organic Spring.

---

# Bookmark Animation

Bookmark

```
1

↓

1.2

↓

1
```

Small downward pull before settling.

---

# Checklist Toggle

Animation

```
Scale

↓

Check

↓

Green

↓

Line-through
```

Visual Style

```css
text-emerald-900

line-through

opacity-80
```

---

# Search Animation

Search expands on focus.

Width

```
+24px
```

Search icon slides slightly right.

---

# 8. Notification Animations

---

# Toast

## Entry

```
Y

24px

↓

0
```

Fade

```
0

↓

100
```

---

## Exit

Fade

↓

Slide Down

---

## Timing

Entry

```
250ms
```

Dismiss

```
200ms
```

Auto Close

```
4 Seconds
```

---

# Notification Badge

Unread indicator pulses every

```
1.2 seconds
```

Animation

```
Dot

↓

Ripple

↓

Fade
```

Very low opacity to remain unobtrusive.

---

# 9. Motion Accessibility Principles

## Respect User Preferences

Support the operating system's **Reduce Motion** preference.

When enabled:

- Disable parallax effects
- Remove large scale animations
- Replace transitions with fades
- Keep interaction feedback immediate

---

## Keyboard Navigation

Motion must never interfere with:

- Focus order
- Screen readers
- Keyboard traversal

---

## Motion Timing

Keep animations short enough to avoid slowing interaction while still communicating state.

Recommended durations:

- **100ms** – Atomic interactions
- **200ms** – Controls and focus
- **300ms** – Components and overlays
- **450ms** – Full view transitions

---

## Motion Hierarchy

Prioritize animations in this order:

1. User feedback (click, hover, focus)
2. Navigation transitions
3. Overlay transitions
4. Content reveal
5. Decorative effects (used sparingly)

---

# Motion Design Principles

OntDekker's motion system reflects the philosophy of slow travel: every movement should feel **purposeful, grounded, and calm**. Rather than relying on flashy transitions, animations reinforce spatial understanding, guide attention, and provide tactile feedback that mirrors natural materials. The result is a cohesive interaction language where every transition contributes to clarity, confidence, and a premium user experience.