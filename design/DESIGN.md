---
name: Technical Precision
colors:
  surface: '#051424'
  surface-dim: '#051424'
  surface-bright: '#2c3a4c'
  surface-container-lowest: '#010f1f'
  surface-container-low: '#0d1c2d'
  surface-container: '#122131'
  surface-container-high: '#1c2b3c'
  surface-container-highest: '#273647'
  on-surface: '#d4e4fa'
  on-surface-variant: '#debec8'
  inverse-surface: '#d4e4fa'
  inverse-on-surface: '#233143'
  outline: '#a68992'
  outline-variant: '#574048'
  surface-tint: '#ffb0cd'
  primary: '#ffb0cd'
  on-primary: '#640039'
  primary-container: '#f751a1'
  on-primary-container: '#570032'
  inverse-primary: '#b4136d'
  secondary: '#bec6e0'
  on-secondary: '#283044'
  secondary-container: '#3f465c'
  on-secondary-container: '#adb4ce'
  tertiary: '#c0c1ff'
  on-tertiary: '#1000a9'
  tertiary-container: '#8083ff'
  on-tertiary-container: '#0d0096'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffd9e4'
  primary-fixed-dim: '#ffb0cd'
  on-primary-fixed: '#3e0022'
  on-primary-fixed-variant: '#8c0053'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#e1e0ff'
  tertiary-fixed-dim: '#c0c1ff'
  on-tertiary-fixed: '#07006c'
  on-tertiary-fixed-variant: '#2f2ebe'
  background: '#051424'
  on-background: '#d4e4fa'
  surface-variant: '#273647'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  pane-gap: 1px
  container-padding: 1rem
  density-tight: 0.25rem
  density-medium: 0.75rem
  sidebar-width: 260px
---

## Brand & Style

This design system is engineered for developers and AI researchers who require clarity amidst high-density data. The brand personality is **analytical, sophisticated, and uncompromisingly precise**. It balances the clinical nature of data science with the vibrant energy of cutting-edge AI.

The visual style is **Modern Corporate with a Technical Edge**. It prioritizes function over decoration, utilizing high-density layouts, subtle monochromatic borders, and a dark-first color strategy to reduce eye strain during long sessions of model evaluation and code review.

## Colors

The palette is anchored in a **Deep Navy** (`#0F172A`) core to provide a stable, professional foundation for complex interfaces. The **Vibrant Pink** (`#EC4899`) serves as the primary action color, used sparingly for high-intent interactions, status highlights, and brand moments.

- **Backgrounds:** Use tiered navy shades to separate panes (e.g., `#0F172A` for the workspace, `#1E293B` for sidebars).
- **Accents:** Use the primary pink for buttons and primary progress indicators.
- **Data Visualization:** Supplement with tertiary indigos and teals to differentiate model outputs and performance metrics.
- **Borders:** Use low-contrast slate tones (`#334155`) to define panes without creating visual noise.

## Typography

The typography system uses **Geist** for its clinical legibility and modern geometric construction. **JetBrains Mono** is utilized for all technical data, code blocks, and chat logs to ensure character distinction (e.g., distinguishing `0` from `O`).

- **Hierarchy:** Use `label-caps` for table headers and section metadata to maximize vertical space.
- **Code & Chat:** All AI-generated content should be rendered in `code-md` for a distinct "machine-output" feel.
- **Density:** Line heights are kept tight (1.4x - 1.5x) to support data-heavy views without sacrificing readability.

## Layout & Spacing

The layout follows a **Fluid Multi-Pane Grid** model, inspired by modern IDEs. Content is organized into modular "panes" that can be resized or collapsed.

- **The 1px Philosophy:** Use 1px gaps between major UI sections (sidebar, main content, inspector) to create a sophisticated, high-tech "tiled" look.
- **Information Density:** Use an 8px base grid but allow for 4px increments in data tables and property panels.
- **Breakpoints:**
  - **Desktop (1440px+):** 3-column layout (Navigation | Workspace | Inspector).
  - **Tablet (768px - 1439px):** 2-column layout; Inspector moves to a drawer.
  - **Mobile:** Single column; prioritize chat/result stream with bottom-sheet configuration.

## Elevation & Depth

This design system avoids heavy drop shadows in favor of **Tonal Layering** and **Low-Contrast Outlines**.

- **Surface Levels:** 
  - Level 0 (Background): `#020617`
  - Level 1 (Panes): `#0F172A`
  - Level 2 (Inputs/Cards): `#1E293B`
- **Borders:** Define depth through 1px solid borders using `#334155`. 
- **Interaction:** On hover, increase border brightness rather than adding a shadow. Only use shadows for "floating" elements like context menus or tooltips, using a sharp, small-radius dark shadow.

## Shapes

To maintain a technical and "constructed" feel, the design system utilizes **Soft** corners.

- **Standard Radius:** 4px (0.25rem) for buttons, inputs, and cards.
- **Inner Elements:** Use 2px radius for nested elements (like chips inside a card) to maintain visual nesting ratios.
- **Strictness:** Avoid pill-shaped buttons; use the standard 4px radius to reinforce the professional, tool-like aesthetic.

## Components

### Buttons
- **Primary:** Pink background, white text, no shadow.
- **Ghost:** No background, subtle grey border, pink text on hover.

### Data Tables
- Use `code-sm` for cell values. 
- Headers use `label-caps` with a subtle bottom border. 
- Row hover state uses a subtle background shift to `#1E293B`.

### AI Chat Bubbles
- **User:** Subtle slate border with `body-md`.
- **Assistant:** Deep navy background with `code-md` for technical output.
- **Source Citations:** Small 4px-radius chips in the footer of the bubble.

### Panes & Containers
- Every pane must have a title bar with a `label-caps` title and utility icons (collapse, settings) in the top-right.

### Input Fields
- Dark backgrounds (`#0F172A`) with a constant 1px border.
- Active state: Primary pink border with a 1px pink outer glow.