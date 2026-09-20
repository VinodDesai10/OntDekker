# OntDekker Visual Identity & Art Direction System

> **Version:** 1.0  
> **Document Type:** Visual Identity & Art Direction Guide  
> **Role:** Senior Visual Designer  
> **Purpose:** Define the complete visual identity, brand language, color psychology, typography, imagery, layout principles, and art direction standards for OntDekker.

---

# Table of Contents

1. Brand Identity
2. Visual Philosophy
3. Color System
4. Typography System
5. Photography & Illustration
6. Layout & Whitespace
7. Card & Surface System
8. Contrast & Accessibility
9. Responsive Visual System
10. Brand Consistency Rules

---

# 1. Brand Identity

## Brand Meaning

**OntDekker** (Dutch for *Discoverer*) represents mindful exploration, slow travel, meaningful human connections, and authentic cultural experiences.

Unlike traditional travel applications, OntDekker avoids overstimulation and instead promotes calm, intentional discovery.

---

## Design Inspiration

The visual identity combines three complementary design philosophies.

### Swiss Modernism

- Precision grids
- Strong typography
- Purposeful whitespace
- Minimal ornamentation

---

### Editorial Design

Inspired by premium travel publications such as:

- Cereal
- Kinfolk
- National Geographic Traveler

Characteristics include:

- Calm layouts
- Long-form readability
- Organic paper tones
- Photography-first presentation

---

### Functional Outdoor Design

Inspired by premium expedition equipment.

Visual characteristics:

- Clear labels
- Durable UI elements
- Practical information hierarchy
- Utility-first interfaces

---

# 2. Visual Philosophy

The interface should always feel:

- Calm
- Warm
- Authentic
- Premium
- Human

Never:

- Loud
- Artificial
- Overly colorful
- Gamified
- Distracting

---

## Design Principles

### Editorial First

Content should feel like reading a beautifully designed travel journal.

---

### Minimal Interfaces

Remove unnecessary visual noise.

Whitespace is treated as an intentional design element.

---

### Human-Centered

Photography, stories, and communities always take precedence over interface chrome.

---

# 3. Color System

## Primary Palette

| Color | Hex | Purpose |
|--------|------|-----------------------------|
| Sand Cream | `#FBF9F4` | Main application canvas |
| Deep Charcoal | `#111111` | Primary typography |
| Glacier Mist | `#EAE7DF` | Borders & separators |
| Backcountry Forest | `#0F5132` | Success & verification |
| Alpine Ridge Blue | `#1D4ED8` | Technical information |
| Sunset Amber | `#F59E0B` | Warnings & highlights |

---

## Color Psychology

### Sand Cream

```
#FBF9F4
```

Creates warmth while reducing eye fatigue.

Represents:

- Paper
- Nature
- Calmness

---

### Deep Charcoal

```
#111111
```

Used for:

- Titles
- Important information
- Primary actions

Represents authority without the harshness of pure black.

---

### Backcountry Forest

```
#0F5132
```

Used for:

- Verified guides
- Success messages
- Completed tasks

Represents:

- Safety
- Nature
- Growth

---

### Alpine Ridge

```
#1D4ED8
```

Used only for:

- Technical markers
- Navigation
- Coordinates
- Specialized information

---

### Sunset Amber

```
#F59E0B
```

Used for:

- Warnings
- Milestones
- Alerts
- User achievements

---

### Glacier Mist

```
#EAE7DF
```

Used for:

- Dividers
- Borders
- Surface separation

---

# 4. Typography System

Typography provides the structural backbone of the interface.

---

## Display Font

**Space Grotesk**

Alternative

**Inter Bold**

Used for:

- Hero titles
- Page headings
- Editorial headers

---

## Body Font

**Inter**

Used for:

- Paragraphs
- Descriptions
- Forms
- Navigation
- Buttons

---

## Technical Font

**JetBrains Mono**

Used exclusively for:

- Coordinates
- Statistics
- Metadata
- Read time
- Dates
- Distances
- Pack weights

---

## Type Scale

### H1

```css
font-display
font-bold
text-3xl
tracking-tight
text-gray-900
```

---

### H2

```css
font-display
font-bold
text-2xl
tracking-tight
```

---

### H3

```css
font-display
font-bold
text-base
```

---

### Body

```css
font-sans
text-sm
leading-relaxed
text-gray-600
```

---

### Metadata

```css
font-mono
uppercase
tracking-wider
text-[10px]
```

---

# 5. Photography & Illustration

## Photography Style

Images should feel:

- Authentic
- Naturally lit
- Calm
- Documentary
- Editorial

Avoid:

- HDR processing
- Heavy filters
- Oversaturation
- Artificial lighting

---

## Preferred Subjects

- Mountain trails
- Coastal villages
- Tea gardens
- Forest cabins
- Historic architecture
- Sailing boats
- Expedition equipment
- Local communities

---

## Image Aspect Ratios

### Hero Images

```
21 : 9

16 : 9
```

Used for:

- Community headers
- Expedition banners

---

### Story Cards

```
4 : 3

3 : 2
```

---

### Gallery

```
1 : 1
```

---

## Illustration Style

Use:

- Line maps
- Topographical paths
- Minimal diagrams
- Lucide React icons

Avoid:

- Cartoon characters
- Flat corporate illustrations
- Decorative mascots

---

# 6. Layout & Whitespace

Whitespace is treated as an active design element rather than empty space.

---

## Container Width

```css
max-w-5xl

mx-auto

px-6
```

---

## Section Spacing

```css
space-y-8

space-y-10
```

---

## Internal Card Spacing

```css
space-y-3

space-y-4
```

---

## Inline Spacing

```css
gap-2

gap-3
```

---

## Layout Rhythm

Alternate between:

### Editorial Sections

Large imagery

↓

Generous whitespace

↓

Long-form content

---

### Technical Sections

Dense information

↓

Packing

↓

Maps

↓

Coordinates

↓

Checklists

This variation prevents visual fatigue.

---

# 7. Card & Surface System

## Surface Hierarchy

```
Canvas

↓

Cards

↓

Widgets

↓

Buttons
```

---

## Canvas

```css
bg-[#fbf9f4]
```

---

## Cards

```css
bg-white

border

border-gray-100

rounded-3xl

shadow-xs
```

---

## Hero Panels

```css
rounded-3xl
```

---

## Buttons

```css
rounded-xl
```

---

## Badges

```css
rounded-lg

rounded-full
```

---

## Glassmorphism

Used **only** for:

- Sticky headers
- Floating navigation
- Toasts
- Overlay navigation

Implementation

```css
backdrop-blur-md

bg-white/80

border-b
```

Never apply glassmorphism to regular content cards.

---

# 8. Contrast & Accessibility

OntDekker follows **WCAG AA** accessibility standards.

---

## Text Contrast

Primary text

```
#111111
```

on

```
#FFFFFF

or

#FBF9F4
```

Maintains a contrast ratio exceeding **10:1**.

---

## Metadata

Muted text must still maintain a minimum **4.5:1** contrast ratio.

---

## Interactive Elements

All controls include:

- Visible focus outlines
- Keyboard navigation
- High-contrast states

---

## Icons

Icons should never communicate meaning through color alone.

Always pair color with:

- Labels
- Text
- Semantic indicators

---

# 9. Responsive Visual System

## Desktop

Maximum width

```
max-w-5xl

or

max-w-7xl
```

---

## Standard Grid

```
12 Columns
```

Feed

```
8 Columns
```

Sidebar

```
4 Columns
```

---

## Tablet

Maintain two-column layouts where possible.

Collapse secondary panels below primary content when space becomes limited.

---

## Mobile

Layout transforms into:

```
Top Navigation

↓

Content

↓

Floating Create Button

↓

Bottom Navigation
```

All content becomes single-column.

---

## Responsive Principles

- Preserve generous spacing
- Avoid horizontal scrolling
- Keep touch targets accessible
- Prioritize readable line lengths

---

# 10. Brand Consistency Rules

## Color Usage

✅ Use:

- Warm neutrals
- Natural earth tones
- Flat semantic colors

❌ Avoid:

- Neon colors
- Oversaturated gradients
- Artificial rainbow palettes

---

## Photography

✅ Use:

- Authentic travel
- Natural lighting
- Quiet landscapes
- Human stories

❌ Avoid:

- Stock-style business imagery
- Over-edited photos
- Unrealistic HDR effects

---

## Interface Styling

✅ Prefer:

- White cards
- Thin borders
- Large whitespace
- Editorial typography

❌ Avoid:

- Heavy shadows
- Decorative textures
- Overlapping UI
- Excessive visual density

---

## Iconography

Use a single icon library:

**Lucide React**

Guidelines:

- Consistent `strokeWidth={2}`
- Monochrome styling
- Minimal visual weight

---

## Technical Aesthetic

Never display:

- Fake terminal logs
- System telemetry
- Mock server statistics
- Developer-themed decorations
- Artificial "online" indicators

The interface should always feel like a thoughtfully curated travel journal—not a command center.

---

# Visual Identity Principles

The OntDekker visual identity is rooted in the philosophy that **less visual noise creates deeper engagement**. Every color, typeface, photograph, and layout decision supports a slower, more intentional way of exploring the world. Inspired by Swiss modernism, editorial publishing, and functional outdoor design, the interface prioritizes clarity, authenticity, and timeless elegance over trends or visual excess.