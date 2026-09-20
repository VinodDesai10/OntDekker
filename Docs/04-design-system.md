# OntDekker Design System Specification

> **Version:** 1.0  
> **Document Type:** Design System Specification  
> **Purpose:** Define the visual language, design tokens, reusable components, interaction patterns, accessibility standards, and responsive guidelines that create OntDekker's premium Swiss-Editorial + Tech-Minimal aesthetic.

---

# Table of Contents

1. Design Principles
2. Design Tokens
3. Typography System
4. Layout & Grid System
5. Elevation & Shape System
6. Component Library
7. Motion & Animation System
8. Accessibility Standards
9. Responsive Guidelines

---

# 1. Design Principles

OntDekker follows a **Swiss Editorial** design philosophy combined with **modern product minimalism**.

The design language prioritizes:

- Generous whitespace
- Editorial typography
- Calm warm-neutral colors
- Utility over decoration
- Smooth micro-interactions
- Human-centered interfaces

---

# Core Design Principles

## Minimal Interfaces

Every screen should contain only information relevant to the current task.

---

## Editorial Hierarchy

Large typography paired with generous spacing creates an elegant reading experience.

---

## Organic Color Palette

Avoid saturated colors.

Prefer warm neutrals combined with restrained semantic accents.

---

## Purposeful Motion

Animations should communicate state changes rather than decorate the interface.

---

# 2. Design Tokens

---

## Color Palette

| Token | Hex | Usage |
|---------|------|----------------------------|
| Canvas Background | `#FBF9F4` | Primary application background |
| Cream Card | `#FCFBF9` | Cards & widgets |
| Border Sand | `#EAE7DF` | Borders & dividers |
| Ink Solid | `#0A0A0A` | Headings & primary actions |
| Charcoal Body | `#374151` | Paragraph text |
| Muted Slate | `#9CA3AF` | Metadata & captions |
| Moss Green | `#059669` | Success states |
| Ozone Blue | `#1D4ED8` | Accent labels |
| Amber Ochre | `#B45309` | Alerts & warnings |

---

## Tailwind Token Reference

```css
Canvas
bg-[#fbf9f4]

Cards
bg-[#fcfbf9]

Borders
border-[#eae7df]

Primary Text
text-gray-950

Body
text-gray-700

Muted
text-gray-400

Success
bg-emerald-50
text-emerald-700

Accent
bg-blue-50
text-blue-700

Warning
bg-amber-50
text-amber-700
```

---

# 3. Typography System

---

## Font Families

```css
Inter
```

Primary UI Font

Used for:

- Headings
- Body
- Buttons
- Forms

---

```css
JetBrains Mono
```

Used for:

- Metadata
- Statistics
- Pack Weights
- Read Time
- Status Indicators

---

## Heading Scale

| Element | Style |
|-----------|--------------------------------------------|
| H1 | font-sans font-bold tracking-tight |
| H2 | font-sans font-semibold tracking-tight |
| H3 | font-sans font-semibold |
| H4 | font-medium |

---

## Body Typography

```css
font-sans
text-sm
leading-relaxed
text-gray-700
```

---

## Metadata

```css
font-mono
uppercase
tracking-wider
text-[10px]
text-gray-400
```

---

# 4. Layout & Grid System

---

## Container Width

```css
max-w-5xl
mx-auto
px-6
```

---

## Standard Grid

```css
grid-cols-12
gap-8
```

---

## Feed Layout

```
Desktop

┌───────────────┬───────────────┐
│               │               │
│ Feed (8)      │ Sidebar (4)   │
│               │               │
└───────────────┴───────────────┘
```

---

## Grid Classes

Feed

```css
col-span-12
md:col-span-8
```

Sidebar

```css
col-span-12
md:col-span-4
```

---

## Spacing Scale

| Component | Padding |
|-----------|----------|
| Main Views | `space-y-8 pb-20` |
| Cards | `p-6` |
| Medium Widgets | `p-5` |
| Nested Components | `p-4` |
| Forms | `p-3` |

---

# 5. Elevation & Shape System

---

## Border Radius

| Component | Radius |
|-----------|----------|
| Hero Cards | `rounded-3xl` |
| Standard Cards | `rounded-2xl` |
| Buttons | `rounded-xl` |
| Chips | `rounded-full` |

---

## Shadow System

### Default

No shadow

```css
border
border-gray-100
```

---

### Hover

```css
shadow-xs

shadow-sm
```

---

### Modal

```css
shadow-2xl

backdrop-blur-xs

bg-black/45
```

---

# 6. Component Library

---

# Buttons

---

## Primary Button

### Purpose

High-priority actions.

Examples

- Invite Guide
- Message
- Publish Story

---

### Styling

```css
bg-black

text-white

rounded-xl

font-bold

shadow-xs

hover:bg-neutral-800

transition-all
```

---

## Secondary Button

### Purpose

Supporting actions.

Examples

- Cancel
- View Profile

---

### Styling

```css
bg-gray-50

text-gray-800

border

rounded-xl

hover:bg-gray-100
```

---

## Icon Buttons

Examples

- Bookmark
- Like
- Favorite

---

### Default

```css
bg-white

border-gray-100

text-gray-400
```

---

### Active

```css
bg-amber-50

border-amber-200

text-amber-500
```

---

# Cards

Standard Card

```tsx
<div className="
bg-white
border
border-gray-100
rounded-3xl
p-6
space-y-4
shadow-xs
">
```

---

## Hover

```css
hover:shadow-md

hover:scale-[1.002]
```

---

## Internal Divider

```css
border-b

border-gray-100
```

---

# Inputs

---

## Base Style

```css
w-full

bg-gray-50

border

border-gray-200

rounded-xl

px-3.5

py-2.5

text-sm

transition-all
```

---

## Focus

```css
focus:bg-white

focus:ring-1.5

focus:ring-black

focus:border-black
```

---

# Select

Same styling as Inputs with

```css
font-medium
```

---

# Badges

---

## Verification Badge

```css
bg-emerald-50

text-emerald-700

border-emerald-100

rounded-full

px-2.5

py-0.5
```

Used for

- Verified Guides
- Verified Creators
- Expedition Leaders

---

## Weight Badge Variants

| Category | Style |
|-----------|-------------------|
| Ultralight | Teal |
| Lightweight | Emerald |
| Standard | Amber |
| Heavy | Rose |

---

# Progress Bar

Track

```css
w-full

bg-gray-100

h-1.5

rounded-full
```

Fill

```css
transition-all

duration-500
```

Dynamic colors

- Emerald
- Amber
- Rose

---

# 7. Motion & Animation System

Animations are subtle, fast, and functional.

---

## Page Entrance

```tsx
initial={{
opacity:0,
y:15
}}

animate={{
opacity:1,
y:0
}}
```

Duration

```
0.2s–0.3s
```

---

## View Transitions

Wrapped using

```tsx
<AnimatePresence>
```

---

## Tabs

Animated underline

Smooth sliding indicator

---

## Expand / Collapse

```tsx
initial={{
height:0,
opacity:0
}}

animate={{
height:"auto",
opacity:1
}}
```

---

## Checklist Toggle

Animation

```
Scale

↓

Check

↓

Line-through

↓

Green Text
```

Visual State

```css
text-emerald-900

line-through

opacity-80
```

---

## Hover Motion

Cards

```
1.000

↓

1.002
```

Buttons

```
Shadow Increase

↓

Background Transition
```

---

# 8. Accessibility Standards

---

## Focus Indicators

Every interactive element must provide

```css
focus:ring-black
```

---

## Contrast

All text must maintain

```
WCAG AA
```

Minimum

```
4.5 : 1
```

---

## Icons

Icons must never communicate state alone.

Always pair with

- Text
- Labels
- Color

---

## Forms

Every field includes

- Semantic Label
- Focus State
- Keyboard Navigation

---

## Screen Readers

Support

- aria-live
- aria-current
- aria-label
- role="tab"
- role="listbox"

---

# 9. Responsive Guidelines

---

## Desktop

```
Sidebar

+

Workspace

+

Context Panel
```

---

## Tablet

```
Sidebar

↓

Workspace
```

---

## Mobile

```
Top Bar

↓

Content

↓

Floating Create Button

↓

Bottom Navigation
```

---

## Grid Behavior

Desktop

```
12 Columns
```

Mobile

```
1 Column
```

---

## Tabs

Desktop

```
Horizontal
```

Mobile

```css
overflow-x-auto

whitespace-nowrap

scrollbar-none
```

---

## Forms

Desktop

Multi-column layouts

↓

Mobile

Single-column layouts

---

# Design Guidelines

## Do

- Use generous whitespace
- Prioritize readability
- Keep interactions subtle
- Maintain editorial hierarchy
- Preserve calm visual rhythm
- Use semantic colors intentionally

---

## Don't

- Use saturated gradients
- Overuse shadows
- Crowd layouts
- Introduce unnecessary visual noise
- Display technical logs or developer information
- Use animations without purpose

---

# Design Philosophy

OntDekker embraces a **Swiss-Editorial, utility-first design language** built around clarity, restraint, and thoughtful travel. Every component, animation, spacing rule, and color choice exists to support mindful exploration rather than distraction.

The result is an interface that feels timeless, elegant, and calm—allowing stories, communities, expeditions, and human connections to remain the true focus of the experience.